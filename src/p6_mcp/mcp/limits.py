"""Output-size guards so a tool result never blows out a model's context.

Strategy (ADR-0005): serialize, measure, and if over budget drop items from the
end of the largest list until it fits, marking ``truncated`` and returning a
``next_offset`` the caller can page from.
"""

from __future__ import annotations

import json
from typing import Any

from p6_mcp.services.query.serialize import iso

_MIN_ITEMS = 1


def serialized_size(payload: Any) -> int:
    """Byte length of the JSON encoding."""
    return len(json.dumps(iso(payload), ensure_ascii=False, default=str).encode("utf-8"))


def enforce(payload: dict[str, Any], max_bytes: int) -> dict[str, Any]:
    """Shrink ``payload`` in place until it fits the byte budget.

    Only ``items``-style lists are trimmed; scalar summary fields are always
    preserved so the caller still learns the totals.
    """
    if serialized_size(payload) <= max_bytes:
        return payload
    out = dict(payload)
    list_keys = [k for k, v in out.items() if isinstance(v, list) and len(v) > _MIN_ITEMS]
    if not list_keys:
        out["truncated"] = True
        out["truncation_note"] = (
            f"Response exceeds the {max_bytes} byte budget and has no paginable "
            "list to trim; request fewer fields or a narrower filter."
        )
        return out
    biggest = max(list_keys, key=lambda k: serialized_size(out[k]))
    items = list(out[biggest])
    original = len(items)
    # Binary search the largest prefix that fits.
    lo, hi = _MIN_ITEMS, original
    best = _MIN_ITEMS
    while lo <= hi:
        mid = (lo + hi) // 2
        out[biggest] = items[:mid]
        if serialized_size(out) <= max_bytes:
            best = mid
            lo = mid + 1
        else:
            hi = mid - 1
    out[biggest] = items[:best]
    out["truncated"] = True
    out["returned"] = best
    offset = int(out.get("offset") or 0)
    out["next_offset"] = offset + best
    out["truncation_note"] = (
        f"Trimmed {biggest} from {original} to {best} entries to stay within "
        f"{max_bytes} bytes. Page with offset={offset + best}, or pass "
        "fields=[...] / verbosity='compact' to shrink each row."
    )
    return out
