"""Progress, status-update hygiene, variances, and behind-schedule analysis."""

from __future__ import annotations

from typing import Any

from p6_mcp.domain.activity import Activity
from p6_mcp.domain.project import Project
from p6_mcp.domain.schedule import Schedule
from p6_mcp.services.analysis.cost import activity_costs
from p6_mcp.services.analysis.dcma import _baseline_finish_map


def progress_summary(sch: Schedule, projects: list[Project]) -> dict[str, Any]:
    acts = sch.activities_of(projects)
    dd = sch.data_date(projects[0] if projects else None)
    n = len(acts)
    complete = sum(1 for a in acts if a.is_completed)
    active = sum(1 for a in acts if a.is_in_progress)
    not_started = n - complete - active
    od = rd = 0.0
    act_units = rem_units = 0.0
    bud_cost = act_cost = rem_cost = 0.0
    phys_weight = phys_sum = 0.0
    for a in acts:
        od += a.original_duration_hours
        rd += a.remaining_duration_hours
        act_units += a.num("act_work_qty") + a.num("act_equip_qty")
        rem_units += a.num("remain_work_qty") + a.num("remain_equip_qty")
        c = activity_costs(sch, a)
        bud_cost += c["budgeted"]
        act_cost += c["actual"]
        rem_cost += c["remaining"]
        phys_weight += a.original_duration_hours
        phys_sum += a.original_duration_hours * a.percent_complete() / 100.0
    finish = max((a.finish for a in acts if a.finish and not a.is_loe), default=None)
    days_to_finish = None
    if dd and finish and finish > dd:
        cal = sch.default_calendar
        if projects and projects[0].clndr_id:
            cal = sch.calendars_by_id.get(projects[0].clndr_id, cal)
        if cal:
            days_to_finish = round(cal.work_hours_between(dd, finish) / cal.day_hours, 1)
    tot_assign = sum(1 for x in sch.assignments if x.proj_id in {p.proj_id for p in projects})
    return {
        "data_date": dd,
        "activity_counts": {
            "total": n,
            "completed": complete,
            "in_progress": active,
            "not_started": not_started,
        },
        "percent_complete": {
            "by_activity_count": round(complete / n * 100, 1) if n else 0.0,
            "by_duration": round((od - rd) / od * 100, 1) if od else 0.0,
            "by_units": round(act_units / (act_units + rem_units) * 100, 1)
            if act_units + rem_units
            else 0.0,
            "by_cost": round(act_cost / bud_cost * 100, 1) if bud_cost else 0.0,
            "duration_weighted_activity_pct": round(phys_sum / phys_weight * 100, 1)
            if phys_weight
            else 0.0,
        },
        "cost": {
            "budgeted": round(bud_cost, 2),
            "actual": round(act_cost, 2),
            "remaining": round(rem_cost, 2),
        },
        "forecast_finish": finish,
        "working_days_to_finish": days_to_finish,
        "assignment_count": tot_assign,
    }


def behind_schedule(
    sch: Schedule,
    projects: list[Project],
    days_late_min: float = 0.0,
    vs: str = "baseline",
) -> list[dict[str, Any]]:
    """Activities forecast/finished later than their baseline (or planned) finish."""
    bl_map, source = _baseline_finish_map(sch, projects)
    out: list[dict[str, Any]] = []
    for a in sch.activities_of(projects):
        ref = bl_map.get(a.code) if vs == "baseline" else a.planned_finish
        cur = a.finish
        if ref is None or cur is None or cur <= ref:
            continue
        cal = sch.calendar_for(a)
        late_days = cal.work_hours_between(ref, cur) / cal.day_hours if cal else (cur - ref).days
        if late_days >= days_late_min:
            out.append(
                {
                    "task_code": a.code,
                    "task_name": a.name,
                    "status": a.status_label,
                    "reference_finish": ref,
                    "current_finish": cur,
                    "days_late": round(late_days, 1),
                    "total_float_days": sch.hours_to_days(a, a.total_float_hours),
                    "comparison_source": source,
                }
            )
    out.sort(key=lambda d: (-float(d["days_late"]), str(d["task_code"])))
    return out


def status_update_check(sch: Schedule, projects: list[Project]) -> dict[str, Any]:
    """Data-date hygiene: things that should have happened by DD but didn't,
    and internally inconsistent status/date/duration combinations."""
    dd = sch.data_date(projects[0] if projects else None)
    should_have_started: list[Activity] = []
    should_have_finished: list[Activity] = []
    active_no_actual_start: list[Activity] = []
    complete_no_actual_finish: list[Activity] = []
    remaining_anomalies: list[dict[str, Any]] = []
    actuals_after_dd: list[Activity] = []
    for a in sch.activities_of(projects):
        if dd is not None:
            if a.is_not_started and a.early_start and a.early_start < dd:
                should_have_started.append(a)
            if not a.is_completed and a.early_finish and a.early_finish < dd:
                should_have_finished.append(a)
            if (a.act_start and a.act_start > dd) or (a.act_finish and a.act_finish > dd):
                actuals_after_dd.append(a)
        if a.is_in_progress and a.act_start is None:
            active_no_actual_start.append(a)
        if a.is_completed and a.act_finish is None:
            complete_no_actual_finish.append(a)
        if a.is_completed and a.remaining_duration_hours > 0:
            remaining_anomalies.append(
                {"task_code": a.code, "issue": "completed but remaining duration > 0"}
            )
        if a.is_in_progress and a.remaining_duration_hours == 0 and not a.is_milestone:
            remaining_anomalies.append(
                {"task_code": a.code, "issue": "in progress with zero remaining duration"}
            )
        if a.is_not_started and (a.act_start or a.act_finish):
            remaining_anomalies.append(
                {"task_code": a.code, "issue": "not started but has actual dates"}
            )

    def codes(lst: list[Activity]) -> list[str]:
        return sorted(a.code for a in lst)

    return {
        "data_date": dd,
        "should_have_started": codes(should_have_started),
        "should_have_finished": codes(should_have_finished),
        "in_progress_without_actual_start": codes(active_no_actual_start),
        "complete_without_actual_finish": codes(complete_no_actual_finish),
        "actuals_after_data_date": codes(actuals_after_dd),
        "remaining_duration_anomalies": sorted(
            remaining_anomalies, key=lambda d: str(d["task_code"])
        ),
    }


def invalid_dates(sch: Schedule, projects: list[Project]) -> list[dict[str, Any]]:
    dd = sch.data_date(projects[0] if projects else None)
    out: list[dict[str, Any]] = []
    if dd is None:
        return out
    for a in sch.activities_of(projects):
        problems: list[str] = []
        if a.act_start and a.act_start > dd:
            problems.append("actual start after data date")
        if a.act_finish and a.act_finish > dd:
            problems.append("actual finish after data date")
        if not a.is_completed:
            fc = a.early_finish or a.planned_finish
            if fc is not None and fc < dd:
                problems.append("forecast finish before data date")
            fs = a.early_start or a.planned_start
            if a.is_not_started and fs is not None and fs < dd:
                problems.append("forecast start before data date")
        if problems:
            out.append({"task_code": a.code, "task_name": a.name, "problems": problems})
    return sorted(out, key=lambda d: str(d["task_code"]))


def activity_variances(
    sch: Schedule, projects: list[Project], vs: str = "baseline"
) -> list[dict[str, Any]]:
    """Start/finish variance in working days vs baseline or planned dates."""
    _, source = _baseline_finish_map(sch, projects)
    bl_acts: dict[str, Activity] = {}
    if vs == "baseline":
        bl_ids = {p.sum_base_proj_id for p in projects if p.sum_base_proj_id is not None} | {
            bp.proj_id
            for bp in sch.baseline_projects
            if bp.orig_proj_id in {p.proj_id for p in projects}
        }
        bl_acts = {a.code: a for a in sch.activities if a.proj_id in bl_ids}
    out: list[dict[str, Any]] = []
    for a in sch.activities_of(projects):
        if vs == "baseline":
            bl = bl_acts.get(a.code)
            ref_start = (bl.start or bl.planned_start) if bl else None
            ref_finish = (bl.finish or bl.planned_finish) if bl else None
        else:
            ref_start, ref_finish = a.planned_start, a.planned_finish
        cal = sch.calendar_for(a)
        if cal is None:
            continue
        row: dict[str, Any] = {"task_code": a.code, "task_name": a.name, "status": a.status_label}
        has_var = False
        if ref_start and a.start:
            v = cal.work_hours_between(ref_start, a.start) / cal.day_hours
            row["start_variance_days"] = round(v, 1)
            has_var = has_var or abs(v) > 0.01
        if ref_finish and a.finish:
            v = cal.work_hours_between(ref_finish, a.finish) / cal.day_hours
            row["finish_variance_days"] = round(v, 1)
            has_var = has_var or abs(v) > 0.01
        if has_var:
            row["comparison"] = source if vs == "baseline" else "planned dates"
            out.append(row)
    out.sort(key=lambda d: -abs(float(d.get("finish_variance_days") or 0)))
    return out
