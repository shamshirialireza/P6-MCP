"""Constraint inventory and hygiene."""

from __future__ import annotations

from typing import Any

from p6_mcp.domain.base import HARD_CONSTRAINTS
from p6_mcp.domain.project import Project
from p6_mcp.domain.schedule import Schedule


def constraints(
    sch: Schedule, projects: list[Project], constraint_type: str | None = None
) -> dict[str, Any]:
    """All constrained activities with hard/soft classification and
    constraints dated before the data date (stale)."""
    dd = sch.data_date(projects[0] if projects else None)
    rows: list[dict[str, Any]] = []
    hard = soft = stale = 0
    for a in sch.activities_of(projects):
        entries = []
        if a.cstr_type:
            entries.append((a.cstr_type, a.cstr_date, "primary"))
        if a.f("cstr_type2"):
            entries.append((a.f("cstr_type2"), a.date("cstr_date2"), "secondary"))
        for ctype, cdate, slot in entries:
            if constraint_type and ctype != constraint_type:
                continue
            is_hard = ctype in HARD_CONSTRAINTS
            is_stale = bool(dd and cdate and cdate < dd and not a.is_completed)
            hard += is_hard
            soft += not is_hard
            stale += is_stale
            rows.append(
                {
                    "task_code": a.code,
                    "task_name": a.name,
                    "status": a.status_label,
                    "slot": slot,
                    "constraint_type": ctype,
                    "constraint": a.cstr_label if slot == "primary" else ctype,
                    "constraint_date": cdate,
                    "classification": "hard" if is_hard else "soft",
                    "stale_before_data_date": is_stale,
                }
            )
    rows.sort(key=lambda d: (str(d["task_code"]), str(d["slot"])))
    return {
        "data_date": dd,
        "total": len(rows),
        "hard": hard,
        "soft": soft,
        "stale_before_data_date": stale,
        "constraints": rows,
    }
