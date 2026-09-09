"""Pagination + sorting helpers shared by every list-returning service."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Sequence, TypeVar

from p6_mcp.exceptions import InvalidArgumentError

T = TypeVar("T")

_SENTINEL_LOW = (0, "", 0.0)


def _sort_key(get: Callable[[T], Any]) -> Callable[[T], tuple[int, Any]]:
    """None-safe, mixed-type-safe sort key (Nones last, stable)."""

    def key(item: T) -> tuple[int, Any]:
        v = get(item)
        if v is None:
            return (3, 0)
        if isinstance(v, datetime):
            return (0, v.isoformat())
        if isinstance(v, bool):
            return (1, int(v))
        if isinstance(v, (int, float)):
            return (1, float(v))
        return (2, str(v).lower())

    return key


def paginate(
    items: Sequence[T],
    *,
    limit: int,
    offset: int,
    max_limit: int = 1000,
    sort_get: Callable[[T], Any] | None = None,
    sort_dir: str = "asc",
) -> tuple[list[T], dict[str, Any]]:
    """Sort + slice; returns (page, envelope-metadata without items)."""
    if limit < 1:
        raise InvalidArgumentError("limit must be >= 1")
    limit = min(limit, max_limit)
    if offset < 0:
        raise InvalidArgumentError("offset must be >= 0")
    if sort_dir not in ("asc", "desc"):
        raise InvalidArgumentError("sort_dir must be 'asc' or 'desc'")
    ordered = list(items)
    if sort_get is not None:
        ordered.sort(key=_sort_key(sort_get), reverse=(sort_dir == "desc"))
    total = len(ordered)
    page = ordered[offset : offset + limit]
    meta: dict[str, Any] = {
        "total": total,
        "offset": offset,
        "limit": limit,
        "returned": len(page),
        "next_offset": offset + limit if offset + limit < total else None,
    }
    return page, meta


def envelope(page_items: list[Any], meta: dict[str, Any]) -> dict[str, Any]:
    """The standard list-tool response envelope."""
    return {**meta, "items": page_items}
