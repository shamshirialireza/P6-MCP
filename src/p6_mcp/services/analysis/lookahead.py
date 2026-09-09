"""Lookahead windows: what starts, finishes, or is in progress soon."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from p6_mcp.domain.project import Project
from p6_mcp.domain.schedule import Schedule


def lookahead(
    sch: Schedule,
    projects: list[Project],
    window_days: int = 28,
    start_from: datetime | None = None,
    group_by: str = "wbs",
) -> dict[str, Any]:
    """Activities starting/finishing/in-progress within the window from the
    data date (or ``start_from``), grouped by WBS path or an activity code type."""
    anchor = start_from or sch.data_date(projects[0] if projects else None)
    if anchor is None:
        anchor = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    horizon = anchor + timedelta(days=window_days)
    starting: list[dict[str, Any]] = []
    finishing: list[dict[str, Any]] = []
    in_progress: list[dict[str, Any]] = []

    def group_key(a: Any) -> str:
        if group_by == "wbs":
            return sch.wbs_path(a.wbs_id) or "(no WBS)"
        for c in sch.codes_by_task.get(a.task_id, []):
            if str(c.get("code_type") or "").lower() == group_by.lower():
                return str(c.get("code_value"))
        return "(unassigned)"

    for a in sch.activities_of(projects):
        if a.is_completed or a.is_loe or a.is_wbs_summary:
            continue
        row = {
            "task_code": a.code,
            "task_name": a.name,
            "group": group_key(a),
            "start": a.start,
            "finish": a.finish,
            "total_float_days": sch.hours_to_days(a, a.total_float_hours),
            "is_critical": a.total_float_hours is not None and a.total_float_hours <= 0,
        }
        if a.is_not_started and a.start and anchor <= a.start <= horizon:
            starting.append(row)
        if a.finish and anchor <= a.finish <= horizon:
            finishing.append(row)
        if a.is_in_progress and (a.finish is None or a.finish > horizon):
            in_progress.append(row)

    def bucketize(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = {}
        for r in sorted(rows, key=lambda x: (x["start"] or datetime.max, str(x["task_code"]))):
            out.setdefault(str(r["group"]), []).append(r)
        return out

    return {
        "window_start": anchor,
        "window_end": horizon,
        "window_days": window_days,
        "group_by": group_by,
        "starting": bucketize(starting),
        "finishing": bucketize(finishing),
        "continuing_in_progress": bucketize(in_progress),
        "counts": {
            "starting": len(starting),
            "finishing": len(finishing),
            "continuing_in_progress": len(in_progress),
        },
    }
