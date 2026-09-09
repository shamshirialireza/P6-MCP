"""XER file-format layer: tokenizer, schema registry, reader, writer.

No business logic lives here — only lossless translation between bytes on disk
and the :class:`~p6_mcp.parser.reader.XerDocument` structure.
"""

from p6_mcp.parser.reader import Table, XerDocument, XerReader
from p6_mcp.parser.writer import XerWriter

__all__ = ["Table", "XerDocument", "XerReader", "XerWriter"]
