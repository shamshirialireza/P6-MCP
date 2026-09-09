"""Milestone extraction with baseline variance."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from p6_mcp.domain.project import Project
from p6_mcp.domain.schedule import Schedule
from p6_mcp.services.analysis.dcma import _baseline_finish_map


def milestones(
    sch: Schedule, projects: list[Project], status: list[str] | None = None
) -> list[dict[str, Any]]:
    bl_map, bl_source = _baseline_finish_map(sch, projects)
    out: list[dict[str, Any]] = []
    for a in sch.activities_of(projects):
        if not a.is_milestone:
            continue
        if status and a.status not in status and a.status_label not in status:
            continue
        date = a.finish if a.task_type == "TT_FinMile" else a.start
        bl = bl_map.get(a.code)
        variance_days = None
        if bl is not None and date is not None:
            cal = sch.calendar_for(a)
            variance_days = round(
                cal.work_hours_between(bl, date) / cal.day_hours, 1
            ) if cal else (date - bl).days
        out.append(
            {
                "task_code": a.code,
                "task_name": a.name,
                "milestone_type": a.type_label,
                "status": a.status_label,
                "date": date,
                "early": a.early_start if a.task_type == "TT_Mile" else a.early_finish,
                "late": a.late_start if a.task_type == "TT_Mile" else a.late_finish,
                "actual": a.act_start if a.task_type == "TT_Mile" else a.act_finish,
                "baseline": bl,
                "variance_days": variance_days,
                "total_float_days": sch.hours_to_days(a, a.total_float_hours),
                "baseline_source": bl_source,
            }
        )
    out.sort(key=lambda d: (d["date"] or datetime.max, str(d["task_code"])))
    return out
