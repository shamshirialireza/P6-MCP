"""Entity → dict serializers with verbosity levels and field selection.

Durations are reported in hours *and* days; day conversion uses the entity's
own calendar (never a hard-coded 8 h/day). Dates serialize as ISO-8601.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from p6_mcp.domain.activity import Activity
from p6_mcp.domain.calendar import Calendar
from p6_mcp.domain.project import Project, Wbs
from p6_mcp.domain.relationship import Relationship
from p6_mcp.domain.resource import Assignment, Resource
from p6_mcp.domain.schedule import Schedule


def iso(v: Any) -> Any:
    """Recursively make a value JSON-serializable."""
    if isinstance(v, datetime):
        return v.isoformat(sep=" ", timespec="minutes")
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, dict):
        return {k: iso(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [iso(x) for x in v]
    return v


def rnd(v: float | None, digits: int = 2) -> float | None:
    return round(v, digits) if v is not None else None


def select_fields(d: dict[str, Any], fields: list[str] | None) -> dict[str, Any]:
    if not fields:
        return d
    return {k: v for k, v in d.items() if k in fields}


def activity_to_dict(
    sch: Schedule,
    a: Activity,
    verbosity: str = "standard",
    fields: list[str] | None = None,
) -> dict[str, Any]:
    """Serialize an activity at compact/standard/full verbosity."""
    cal = sch.calendar_for(a)
    tf_days = sch.hours_to_days(a, a.total_float_hours)
    d: dict[str, Any] = {
        "task_code": a.code,
        "task_name": a.name,
        "status": a.status_label,
        "task_type": a.type_label,
        "wbs_path": sch.wbs_path(a.wbs_id),
        "start": a.start,
        "finish": a.finish,
        "total_float_days": rnd(tf_days),
        "remaining_duration_days": rnd(sch.hours_to_days(a, a.remaining_duration_hours)),
        "percent_complete": rnd(a.percent_complete(), 1),
    }
    if verbosity in ("standard", "full"):
        proj = sch.projects_by_id.get(a.proj_id)
        d.update(
            {
                "task_id": a.task_id,
                "proj_id": a.proj_id,
                "project": proj.short_name if proj else None,
                "original_duration_hours": a.original_duration_hours,
                "original_duration_days": rnd(sch.hours_to_days(a, a.original_duration_hours)),
                "remaining_duration_hours": a.remaining_duration_hours,
                "total_float_hours": a.total_float_hours,
                "free_float_hours": a.free_float_hours,
                "free_float_days": rnd(sch.hours_to_days(a, a.free_float_hours)),
                "early_start": a.early_start,
                "early_finish": a.early_finish,
                "late_start": a.late_start,
                "late_finish": a.late_finish,
                "actual_start": a.act_start,
                "actual_finish": a.act_finish,
                "planned_start": a.planned_start,
                "planned_finish": a.planned_finish,
                "calendar": cal.name if cal else None,
                "constraint": a.cstr_label,
                "constraint_date": a.cstr_date,
                "is_critical": (a.total_float_hours is not None and a.total_float_hours <= 0)
                if not a.is_completed
                else False,
                "on_longest_path": a.driving_path_flag,
                "is_milestone": a.is_milestone,
            }
        )
    if verbosity == "full":
        d["raw_fields"] = a.to_dict()
    return iso(select_fields(d, fields))


def relationship_to_dict(sch: Schedule, r: Relationship) -> dict[str, Any]:
    pred = sch.activities_by_id.get(r.pred_task_id)
    succ = sch.activities_by_id.get(r.task_id)
    lag_days = None
    if succ is not None:
        lag_days = sch.hours_to_days(succ, r.lag_hours)
    return iso(
        {
            "predecessor": pred.code if pred else r.pred_task_id,
            "predecessor_name": pred.name if pred else None,
            "successor": succ.code if succ else r.task_id,
            "successor_name": succ.name if succ else None,
            "type": r.short_type,
            "type_label": r.type_label,
            "lag_hours": r.lag_hours,
            "lag_days": rnd(lag_days),
            "is_lead": r.is_lead,
            "crosses_projects": r.crosses_projects,
            "comments": r.f("comments"),
        }
    )


def project_to_dict(sch: Schedule, p: Project, verbosity: str = "standard") -> dict[str, Any]:
    acts = [a for a in sch.activities if a.proj_id == p.proj_id]
    d: dict[str, Any] = {
        "proj_id": p.proj_id,
        "proj_short_name": p.short_name,
        "is_baseline": p.is_baseline,
        "data_date": p.data_date,
        "plan_start": p.plan_start,
        "plan_end": p.plan_end,
        "scheduled_end": p.scd_end,
        "critical_path_type": p.critical_path_type_label,
        "critical_float_threshold_hours": p.critical_drtn_hr_cnt,
        "activity_count": len(acts),
        "linked_baseline_proj_id": p.sum_base_proj_id,
        "original_proj_id": p.orig_proj_id,
    }
    if verbosity == "full":
        d["raw_fields"] = p.to_dict()
    return iso(d)


def wbs_to_dict(sch: Schedule, w: Wbs, verbosity: str = "standard") -> dict[str, Any]:
    d: dict[str, Any] = {
        "wbs_id": w.wbs_id,
        "proj_id": w.proj_id,
        "wbs_short_name": w.short_name,
        "wbs_name": w.name,
        "parent_wbs_id": w.parent_wbs_id,
        "level": sch.wbs_level(w.wbs_id),
        "path": sch.wbs_path(w.wbs_id),
        "is_project_node": w.is_project_node,
        "status": w.status_label,
        "activity_count": len(sch.activities_by_wbs.get(w.wbs_id, [])),
    }
    if verbosity == "full":
        d["raw_fields"] = w.to_dict()
    return iso(d)


def resource_to_dict(sch: Schedule, r: Resource, verbosity: str = "standard") -> dict[str, Any]:
    cal = sch.calendars_by_id.get(r.clndr_id) if r.clndr_id else None
    rates = sch.rates_by_rsrc.get(r.rsrc_id, [])
    current_rate = rates[-1] if rates else {}
    d: dict[str, Any] = {
        "rsrc_id": r.rsrc_id,
        "rsrc_name": r.name,
        "rsrc_short_name": r.short_name,
        "rsrc_type": r.type_label,
        "parent_rsrc_id": r.parent_rsrc_id,
        "calendar": cal.name if cal else None,
        "active": r.is_active,
        "default_units_per_hour": r.f("def_qty_per_hr"),
        "current_price_per_unit": current_rate.get("cost_per_qty"),
        "current_max_units_per_hour": current_rate.get("max_qty_per_hr"),
        "assignment_count": len(sch.assignments_by_rsrc.get(r.rsrc_id, [])),
    }
    if verbosity == "full":
        d["raw_fields"] = r.to_dict()
    return iso(d)


def assignment_to_dict(sch: Schedule, x: Assignment, verbosity: str = "standard") -> dict[str, Any]:
    act = sch.activities_by_id.get(x.task_id)
    rsrc = sch.resources_by_id.get(x.rsrc_id) if x.rsrc_id else None
    d: dict[str, Any] = {
        "taskrsrc_id": x.taskrsrc_id,
        "task_code": act.code if act else None,
        "task_name": act.name if act else None,
        "resource": rsrc.name if rsrc else None,
        "rsrc_id": x.rsrc_id,
        "role_id": x.role_id,
        "rsrc_type": x.rsrc_type,
        "budgeted_qty": x.budgeted_qty,
        "actual_qty": x.actual_qty,
        "remaining_qty": x.remaining_qty,
        "at_completion_qty": x.at_completion_qty,
        "budgeted_cost": rnd(x.budgeted_cost),
        "actual_cost": rnd(x.actual_cost),
        "remaining_cost": rnd(x.remaining_cost),
        "at_completion_cost": rnd(x.at_completion_cost),
        "start": x.start,
        "finish": x.finish,
    }
    if verbosity == "full":
        d["raw_fields"] = x.to_dict()
    return iso(d)


def calendar_to_dict(
    sch: Schedule,
    c: Calendar,
    include_workweek: bool = True,
    include_exceptions: bool = True,
) -> dict[str, Any]:
    usage = sum(1 for a in sch.activities if a.clndr_id == c.clndr_id)
    d: dict[str, Any] = {
        "clndr_id": c.clndr_id,
        "clndr_name": c.name,
        "type": c.type_label,
        "base_clndr_id": c.base_clndr_id,
        "is_default": bool(c.f("default_flag")),
        "day_hours": c.day_hours,
        "week_hours": c.week_hours,
        "activity_count": usage,
        "used_fallback_workweek": c.used_fallback_workweek,
    }
    if include_workweek:
        d["workweek"] = c.workweek_dict()
    if include_exceptions:
        d["exceptions"] = c.exceptions_list()
    return iso(d)
