"""Low-level XER tokenization: encoding detection and record splitting.

An XER file is a sequence of tab-delimited records, one per line:

* ``ERMHDR<TAB>version<TAB>export date<TAB>...`` — exactly one, first line.
* ``%T<TAB>TABLENAME`` — begins a table.
* ``%F<TAB>field1<TAB>field2...`` — the table's column names.
* ``%R<TAB>val1<TAB>val2...`` — one row (empty trailing fields preserved).
* ``%E`` — end of file marker.

P6 exports cp1252 by default; newer exports may be UTF-8 or UTF-16 with BOM.
P6 strips embedded tabs/newlines on export, so a record never spans lines.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterator

from p6_mcp.exceptions import XerEncodingError

_BOMS: list[tuple[bytes, str]] = [
    (b"\xff\xfe\x00\x00", "utf-32-le"),
    (b"\x00\x00\xfe\xff", "utf-32-be"),
    (b"\xef\xbb\xbf", "utf-8-sig"),
    (b"\xff\xfe", "utf-16-le"),
    (b"\xfe\xff", "utf-16-be"),
]

RECORD_TYPES = frozenset({"ERMHDR", "%T", "%F", "%R", "%E"})


def detect_encoding(data: bytes) -> str:
    """Detect a byte encoding: BOM first, then strict UTF-8, else cp1252.

    cp1252 is P6's historical default and decodes any byte sequence, so it is
    the terminal fallback.
    """
    for bom, name in _BOMS:
        if data.startswith(bom):
            return name
    try:
        data.decode("utf-8", errors="strict")
        return "utf-8"
    except UnicodeDecodeError:
        return "cp1252"


def decode_bytes(data: bytes, encoding: str | None = None) -> tuple[str, str]:
    """Decode file bytes; returns ``(text, encoding_used)``."""
    enc = encoding or detect_encoding(data)
    try:
        return data.decode(enc), enc
    except (UnicodeDecodeError, LookupError) as exc:
        raise XerEncodingError(
            f"Cannot decode file as {enc!r}: {exc}",
            hint="Pass an explicit encoding (e.g. cp1252, utf-8, utf-16).",
        ) from exc


@dataclass(frozen=True, slots=True)
class Record:
    """One tokenized XER line."""

    line_no: int
    kind: str
    values: list[str]


@dataclass(slots=True)
class TokenizeResult:
    """Records plus the physical-format facts needed for byte-identical writes."""

    records: list[Record]
    line_ending: str
    ends_with_newline: bool
    encoding: str


def tokenize(text: str, encoding: str) -> TokenizeResult:
    """Split decoded XER text into :class:`Record` objects.

    Lines whose first token is not a known record type are yielded with kind
    ``"?"`` so the reader can warn without losing data.
    """
    line_ending = "\r\n" if "\r\n" in text else "\n"
    ends_with_newline = text.endswith(("\n", "\r"))
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if normalized.endswith("\n"):
        normalized = normalized[:-1]

    records: list[Record] = []
    for i, line in enumerate(normalized.split("\n"), start=1):
        if line == "" and i > 1:
            continue  # stray blank lines (some tools append them)
        parts = line.split("\t")
        kind = parts[0]
        if kind not in RECORD_TYPES:
            records.append(Record(i, "?", parts))
        else:
            records.append(Record(i, kind, parts[1:]))
    return TokenizeResult(records, line_ending, ends_with_newline, encoding)


def iter_records(data: bytes, encoding: str | None = None) -> Iterator[Record]:
    """Convenience: decode + tokenize, yielding records."""
    text, enc = decode_bytes(data, encoding)
    yield from tokenize(text, enc).records
