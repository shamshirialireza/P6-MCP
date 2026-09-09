"""Lossless XER writer.

Writes an :class:`XerDocument` back to bytes preserving header, table order,
field order, raw values, line endings, and trailing newline — byte-identical
round-trips for untouched documents.
"""

from __future__ import annotations

from pathlib import Path

from p6_mcp.parser.reader import XerDocument


class XerWriter:
    """Serializes an XerDocument back to XER format."""

    def to_text(self, doc: XerDocument) -> str:
        """Render the document to a single string with its original line ending."""
        lines: list[str] = ["ERMHDR\t" + "\t".join(doc.header.values)]
        for table in doc.tables.values():
            lines.append("%T\t" + table.name)
            lines.append("%F\t" + "\t".join(table.fields))
            for row in table.rows:
                lines.append("%R\t" + "\t".join(row))
        lines.append("%E")
        text = doc.line_ending.join(lines)
        if doc.ends_with_newline:
            text += doc.line_ending
        return text

    def to_bytes(self, doc: XerDocument) -> bytes:
        """Render the document to bytes in its original encoding."""
        enc = doc.encoding
        # utf-8-sig/utf-16 emit their BOM automatically via codecs.
        if enc in ("utf-16-le", "utf-16-be"):
            bom = b"\xff\xfe" if enc == "utf-16-le" else b"\xfe\xff"
            return bom + self.to_text(doc).encode(enc)
        return self.to_text(doc).encode(enc)

    def write_path(self, doc: XerDocument, path: str | Path) -> Path:
        """Write the document to disk; returns the resolved path."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(self.to_bytes(doc))
        return p.resolve()
