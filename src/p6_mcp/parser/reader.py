"""XER document model and reader.

The reader is lossless: every table (known or unknown) becomes a generic
:class:`Table` holding raw string values in original order. Typed access is
provided on top via the schema registry; the raw values remain the write-back
source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator

from p6_mcp.exceptions import FileAccessError, XerParseError
from p6_mcp.parser import coercion
from p6_mcp.parser.schema import KNOWN_TABLES, FieldType, field_type
from p6_mcp.parser.tokenizer import TokenizeResult, decode_bytes, tokenize

_COERCERS = {
    FieldType.STR: lambda s: s if s != "" else None,
    FieldType.INT: coercion.parse_int,
    FieldType.FLOAT: coercion.parse_float,
    FieldType.DATE: coercion.parse_date,
    FieldType.BOOL: coercion.parse_bool,
}


@dataclass(slots=True)
class ErmHdr:
    """The ERMHDR line: P6 version, export date, user, database, currency."""

    values: list[str]

    @property
    def version(self) -> str:
        return self.values[0] if self.values else ""

    @property
    def export_date(self) -> str:
        return self.values[1] if len(self.values) > 1 else ""

    @property
    def user_name(self) -> str:
        return self.values[4] if len(self.values) > 4 else ""

    @property
    def database(self) -> str:
        return self.values[5] if len(self.values) > 5 else ""

    @property
    def currency(self) -> str:
        return self.values[7] if len(self.values) > 7 else ""

    def to_dict(self) -> dict[str, str]:
        return {
            "version": self.version,
            "export_date": self.export_date,
            "user_name": self.user_name,
            "database": self.database,
            "currency": self.currency,
            "raw": "\t".join(self.values),
        }


class Table:
    """One XER table: ordered field names + raw string rows."""

    __slots__ = ("name", "fields", "rows", "_field_index", "_typed_cache")

    def __init__(self, name: str, fields: list[str]) -> None:
        self.name = name
        self.fields = fields
        self.rows: list[list[str]] = []
        self._field_index: dict[str, int] = {f: i for i, f in enumerate(fields)}
        self._typed_cache: dict[int, FieldType] = {}

    @property
    def is_known(self) -> bool:
        return self.name in KNOWN_TABLES

    def has_field(self, name: str) -> bool:
        return name in self._field_index

    def raw(self, row: list[str], field_name: str) -> str:
        """Raw string value for a field ('' when missing)."""
        idx = self._field_index.get(field_name)
        if idx is None or idx >= len(row):
            return ""
        return row[idx]

    def value(self, row: list[str], field_name: str) -> Any:
        """Typed value for a field (None when blank/unparseable)."""
        idx = self._field_index.get(field_name)
        if idx is None or idx >= len(row):
            return None
        ft = self._typed_cache.get(idx)
        if ft is None:
            ft = field_type(field_name)
            self._typed_cache[idx] = ft
        return _COERCERS[ft](row[idx])

    def set(self, row: list[str], field_name: str, value: Any) -> None:
        """Write a typed value back into a row's raw storage."""
        idx = self._field_index.get(field_name)
        if idx is None:
            raise KeyError(f"{self.name} has no field {field_name!r}")
        while len(row) < len(self.fields):
            row.append("")
        if value is None:
            row[idx] = ""
        elif isinstance(value, bool):
            row[idx] = coercion.format_bool(value)
        elif isinstance(value, datetime):
            row[idx] = coercion.format_date(value)
        elif isinstance(value, (int, float)):
            row[idx] = coercion.format_number(value)
        else:
            row[idx] = str(value)

    def row_dict(self, row: list[str], typed: bool = True) -> dict[str, Any]:
        """One row as a field→value mapping."""
        if typed:
            return {f: self.value(row, f) for f in self.fields}
        return {f: self.raw(row, f) for f in self.fields}

    def iter_dicts(self, typed: bool = True) -> Iterator[dict[str, Any]]:
        for row in self.rows:
            yield self.row_dict(row, typed)

    def find(self, field_name: str, value: str) -> list[list[str]]:
        """Rows whose raw field equals ``value``."""
        idx = self._field_index.get(field_name)
        if idx is None:
            return []
        return [r for r in self.rows if idx < len(r) and r[idx] == value]

    def __len__(self) -> int:
        return len(self.rows)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Table {self.name} fields={len(self.fields)} rows={len(self.rows)}>"


@dataclass(slots=True)
class XerDocument:
    """A parsed XER file: header + ordered tables + physical-format facts."""

    header: ErmHdr
    tables: dict[str, Table]
    warnings: list[str] = field(default_factory=list)
    encoding: str = "cp1252"
    line_ending: str = "\r\n"
    ends_with_newline: bool = True
    source_path: str | None = None

    def table(self, name: str) -> Table | None:
        return self.tables.get(name.upper())

    def table_or_empty(self, name: str) -> Table:
        t = self.tables.get(name.upper())
        return t if t is not None else Table(name.upper(), [])

    def inventory(self) -> list[dict[str, Any]]:
        """Table name → row/field counts, flagging unknown tables."""
        return [
            {
                "table": t.name,
                "rows": len(t.rows),
                "fields": len(t.fields),
                "known": t.is_known,
            }
            for t in self.tables.values()
        ]


class XerReader:
    """Parses XER bytes/files into :class:`XerDocument` (never raises on content)."""

    def __init__(self, encoding: str | None = None) -> None:
        self._encoding = encoding

    def read_path(self, path: str | Path) -> XerDocument:
        """Read and parse a file from disk."""
        p = Path(path)
        try:
            data = p.read_bytes()
        except OSError as exc:
            raise FileAccessError(
                f"Cannot read {p}: {exc}", hint="Check the path and permissions."
            ) from exc
        doc = self.read_bytes(data)
        doc.source_path = str(p)
        return doc

    def read_bytes(self, data: bytes) -> XerDocument:
        """Parse XER bytes into a document."""
        text, enc = decode_bytes(data, self._encoding)
        return self._build(tokenize(text, enc))

    def _build(self, tok: TokenizeResult) -> XerDocument:
        records = tok.records
        if not records or records[0].kind != "ERMHDR":
            raise XerParseError(
                "File does not start with an ERMHDR record — not an XER file.",
                hint="Confirm the file is a Primavera P6 .xer export.",
            )
        doc = XerDocument(
            header=ErmHdr(records[0].values),
            tables={},
            encoding=tok.encoding,
            line_ending=tok.line_ending,
            ends_with_newline=tok.ends_with_newline,
        )
        current: Table | None = None
        saw_end = False
        for rec in records[1:]:
            if rec.kind == "%T":
                name = rec.values[0].upper() if rec.values else ""
                if not name:
                    doc.warnings.append(f"line {rec.line_no}: %T record with no table name")
                    current = None
                    continue
                current = Table(name, [])
                if name in doc.tables:
                    doc.warnings.append(f"line {rec.line_no}: duplicate table {name}; merging rows")
                    current = doc.tables[name]
                else:
                    doc.tables[name] = current
                if not current.is_known:
                    doc.warnings.append(f"unknown table {name} (parsed generically)")
            elif rec.kind == "%F":
                if current is None:
                    doc.warnings.append(f"line {rec.line_no}: %F outside a table; ignored")
                elif current.fields:
                    pass  # merged duplicate table keeps first field list
                else:
                    current.fields = rec.values
                    current._field_index = {f: i for i, f in enumerate(rec.values)}
            elif rec.kind == "%R":
                if current is None:
                    doc.warnings.append(f"line {rec.line_no}: %R outside a table; dropped")
                else:
                    row = rec.values
                    if len(row) > len(current.fields):
                        doc.warnings.append(
                            f"line {rec.line_no}: {current.name} row has "
                            f"{len(row)} values for {len(current.fields)} fields"
                        )
                    current.rows.append(row)
            elif rec.kind == "%E":
                saw_end = True
            elif rec.kind == "?":
                doc.warnings.append(
                    f"line {rec.line_no}: unrecognized record {rec.values[0]!r}; ignored"
                )
        if not saw_end:
            doc.warnings.append("missing %E end-of-file marker")
        return doc
