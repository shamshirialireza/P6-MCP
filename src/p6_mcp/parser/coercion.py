"""Value coercion between XER string representation and Python types.

Numbers are coerced to ``float`` (ADR-0002): XER stores decimals with at most
6 fractional digits, well within float precision for schedule quantities, and
float keeps the analytics layer fast and NumPy-friendly. Raw strings are always
retained in the document layer, so write-back is lossless regardless.
"""

from __future__ import annotations

from datetime import date, datetime

_DATE_FORMATS = (
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
)


def parse_date(raw: str) -> datetime | None:
    """Parse a P6 date string (``YYYY-MM-DD HH:MM[:SS]``); None if blank/invalid."""
    s = raw.strip()
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def format_date(value: datetime | date | None) -> str:
    """Serialize a datetime back to P6's ``YYYY-MM-DD HH:MM`` format."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return value.strftime("%Y-%m-%d") + " 00:00"


def parse_float(raw: str) -> float | None:
    """Parse a numeric field; None if blank or unparseable."""
    s = raw.strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_int(raw: str) -> int | None:
    """Parse an integer field (IDs, sequence numbers); None if blank/invalid."""
    s = raw.strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        f = parse_float(s)
        return int(f) if f is not None else None


def format_number(value: float | int | None) -> str:
    """Serialize a number the way P6 does (no trailing ``.0`` for integers)."""
    if value is None:
        return ""
    if isinstance(value, int) or float(value).is_integer():
        return str(int(value))
    return repr(float(value))


def parse_bool(raw: str) -> bool | None:
    """Parse a Y/N flag; None if blank."""
    s = raw.strip().upper()
    if not s:
        return None
    return s == "Y"


def format_bool(value: bool | None) -> str:
    """Serialize a flag back to Y/N."""
    if value is None:
        return ""
    return "Y" if value else "N"
