"""DCMA 14-point schedule assessment.

Implements every check with DCMA-EA PAM 200.1 default thresholds and the
standard exemptions (LOE, WBS summaries, completed activities; milestones for
duration/resource checks). Every exemption and threshold is configurable via
:class:`~p6_mcp.services.analysis.thresholds.DcmaThresholds`.
"""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from typing import Any

from p6_mcp.domain.activity import Activity
from p6_mcp.domain.project import Project
from p6_mcp.domain.schedule import Schedule
from p6_mcp.services.analysis.cpm import compute_cpm
from p6_mcp.services.analysis.thresholds import DcmaThresholds

_OFFENDER_CAP = 25


def _check(
    number: int,
    name: str,
    description: str,
    *,
    passed: bool,
    metric: float | None,
    threshold_desc: str,
    count: int,
    eligible: int,
    offenders: list[Activity] | list[str],
    note: str | None = None,
) -> dict[str, Any]:
    codes = [o.code if isinstance(o, Activity) else o for o in offenders]
    out: dict[str, Any] = {
        "check": number,
        "name": name,
        "description": description,
        "passed": passed,
        "metric": round(metric, 2) if metric is not None else None,
        "threshold": threshold_desc,
        "count": count,
        "eligible": eligible,
        "offenders": sorted(codes)[:_OFFENDER_CAP],
        "offenders_truncated": len(codes) > _OFFENDER_CAP,
    }
    if note:
        out["note"] = note
    return out


def _baseline_finish_map(sch: Schedule, projects: list[Project]) -> tuple[dict[str, datetime], str]:
    """task_code -> baseline finish. Uses linked baseline projects when present,
    else planned (target) dates as a documented proxy."""
    bl_ids: set[int] = set()
    for p in projects:
        if p.sum_base_proj_id is not None:
            bl_ids.add(p.sum_base_proj_id)
    for bp in sch.baseline_projects:
        if bp.orig_proj_id in {p.proj_id for p in projects}:
            bl_ids.add(bp.proj_id)
    if bl_ids:
        out: dict[str, datetime] = {}
        for a in sch.activities:
            if a.proj_id in bl_ids:
                fin = a.finish or a.planned_finish
                if fin is not None:
                    out[a.code] = fin
        if out:
            return out, "baseline project in file"
    proxy = {
        a.code: a.planned_finish
        for a in sch.activities_of(projects)
        if a.planned_finish is not None
    }
    return proxy, "planned (target) dates used as baseline proxy — no baseline project in file"


def run_dcma_assessment(
    sch: Schedule,
    projects: list[Project],
    th: DcmaThresholds | None = None,
) -> dict[str, Any]:
    """All 14 checks; returns per-check details plus an overall summary."""
    th = th or DcmaThresholds()
    dd = sch.data_date(projects[0] if projects else None)
    all_acts = sch.activities_of(projects)

    def exempt(a: Activity) -> bool:
        if th.exempt_loe and a.is_loe:
            return True
        return th.exempt_wbs_summary and a.is_wbs_summary

    tasks = [a for a in all_acts if not exempt(a)]
    incomplete = [a for a in tasks if not a.is_completed] if th.exempt_completed else tasks
    non_mile_incomplete = [a for a in incomplete if not a.is_milestone]

    def days(a: Activity, hours: float | None) -> float | None:
        return sch.hours_to_days(a, hours)

    checks: list[dict[str, Any]] = []

    # 1. Missing logic --------------------------------------------------------
    no_pred = [a for a in incomplete if a.task_id not in sch.predecessors_of]
    no_succ = [a for a in incomplete if a.task_id not in sch.successors_of]
    allowed_pred = min(no_pred, key=lambda a: a.start or datetime.max, default=None)
    allowed_succ = max(no_succ, key=lambda a: a.finish or datetime.min, default=None)
    offenders1 = sorted(
        {a.code for a in no_pred if a is not allowed_pred}
        | {a.code for a in no_succ if a is not allowed_succ}
    )
    pct1 = len(offenders1) / len(incomplete) * 100 if incomplete else 0.0
    checks.append(
        _check(
            1,
            "Logic",
            "Incomplete tasks missing a predecessor or successor "
            "(one start and one finish open end allowed)",
            passed=pct1 <= th.missing_logic_pct_max,
            metric=pct1,
            threshold_desc=f"<= {th.missing_logic_pct_max}%",
            count=len(offenders1),
            eligible=len(incomplete),
            offenders=offenders1,
        )
    )

    # Relationship pool: both ends inside the assessed projects, incomplete.
    inc_ids = {a.task_id for a in incomplete}
    rels = [r for r in sch.relationships if r.task_id in inc_ids or r.pred_task_id in inc_ids]

    # 2. Leads ---------------------------------------------------------------
    leads = [r for r in rels if r.lag_hours < 0]
    lead_codes = [
        f"{sch.activities_by_id[r.pred_task_id].code}->{sch.activities_by_id[r.task_id].code}"
        for r in leads
        if r.pred_task_id in sch.activities_by_id and r.task_id in sch.activities_by_id
    ]
    checks.append(
        _check(
            2,
            "Leads",
            "Relationships with negative lag",
            passed=len(leads) <= th.leads_max,
            metric=len(leads) / len(rels) * 100 if rels else 0.0,
            threshold_desc=f"count <= {th.leads_max}",
            count=len(leads),
            eligible=len(rels),
            offenders=lead_codes,
        )
    )

    # 3. Lags ----------------------------------------------------------------
    lags = [r for r in rels if r.lag_hours > 0]
    pct3 = len(lags) / len(rels) * 100 if rels else 0.0
    lag_codes = [
        f"{sch.activities_by_id[r.pred_task_id].code}->{sch.activities_by_id[r.task_id].code}"
        for r in lags
        if r.pred_task_id in sch.activities_by_id and r.task_id in sch.activities_by_id
    ]
    checks.append(
        _check(
            3,
            "Lags",
            "Relationships with positive lag",
            passed=pct3 <= th.lags_pct_max,
            metric=pct3,
            threshold_desc=f"<= {th.lags_pct_max}%",
            count=len(lags),
            eligible=len(rels),
            offenders=lag_codes,
        )
    )

    # 4. Relationship types --------------------------------------------------
    fs = sum(1 for r in rels if r.pred_type == "PR_FS")
    pct4 = fs / len(rels) * 100 if rels else 100.0
    non_fs = [
        f"{sch.activities_by_id[r.pred_task_id].code}->{sch.activities_by_id[r.task_id].code} ({r.short_type})"
        for r in rels
        if r.pred_type != "PR_FS"
        and r.pred_task_id in sch.activities_by_id
        and r.task_id in sch.activities_by_id
    ]
    checks.append(
        _check(
            4,
            "Relationship Types",
            "Finish-to-Start share of relationships",
            passed=pct4 >= th.fs_pct_min,
            metric=pct4,
            threshold_desc=f"FS >= {th.fs_pct_min}%",
            count=len(rels) - fs,
            eligible=len(rels),
            offenders=non_fs,
        )
    )

    # 5. Hard constraints ----------------------------------------------------
    hard = [a for a in incomplete if a.has_hard_constraint]
    pct5 = len(hard) / len(incomplete) * 100 if incomplete else 0.0
    checks.append(
        _check(
            5,
            "Hard Constraints",
            "Mandatory Start/Finish and Start On/Finish On constraints",
            passed=pct5 <= th.hard_constraints_pct_max,
            metric=pct5,
            threshold_desc=f"<= {th.hard_constraints_pct_max}%",
            count=len(hard),
            eligible=len(incomplete),
            offenders=hard,
        )
    )

    # 6. High float ----------------------------------------------------------
    high_float = [
        a
        for a in incomplete
        if (d := days(a, a.total_float_hours)) is not None and d > th.high_float_days
    ]
    pct6 = len(high_float) / len(incomplete) * 100 if incomplete else 0.0
    checks.append(
        _check(
            6,
            "High Float",
            f"Total float > {th.high_float_days:g} working days",
            passed=pct6 <= th.high_float_pct_max,
            metric=pct6,
            threshold_desc=f"<= {th.high_float_pct_max}%",
            count=len(high_float),
            eligible=len(incomplete),
            offenders=high_float,
        )
    )

    # 7. Negative float ------------------------------------------------------
    neg = [a for a in incomplete if a.total_float_hours is not None and a.total_float_hours < 0]
    checks.append(
        _check(
            7,
            "Negative Float",
            "Tasks with total float < 0",
            passed=len(neg) <= th.negative_float_max,
            metric=len(neg) / len(incomplete) * 100 if incomplete else 0.0,
            threshold_desc=f"count <= {th.negative_float_max}",
            count=len(neg),
            eligible=len(incomplete),
            offenders=neg,
        )
    )

    # 8. High duration -------------------------------------------------------
    pool8 = non_mile_incomplete if th.exempt_milestones_from_duration_checks else incomplete
    high_dur = [
        a
        for a in pool8
        if (d := days(a, a.remaining_duration_hours)) is not None and d > th.high_duration_days
    ]
    pct8 = len(high_dur) / len(pool8) * 100 if pool8 else 0.0
    checks.append(
        _check(
            8,
            "High Duration",
            f"Remaining duration > {th.high_duration_days:g} working days",
            passed=pct8 <= th.high_duration_pct_max,
            metric=pct8,
            threshold_desc=f"<= {th.high_duration_pct_max}%",
            count=len(high_dur),
            eligible=len(pool8),
            offenders=high_dur,
        )
    )

    # 9. Invalid dates -------------------------------------------------------
    invalid: list[str] = []
    if dd is not None:
        for a in tasks:
            if a.act_start and a.act_start > dd:
                invalid.append(f"{a.code} (actual start after data date)")
            if a.act_finish and a.act_finish > dd:
                invalid.append(f"{a.code} (actual finish after data date)")
            if not a.is_completed:
                fc = a.early_finish or a.planned_finish
                if fc is not None and fc < dd:
                    invalid.append(f"{a.code} (forecast finish before data date)")
    checks.append(
        _check(
            9,
            "Invalid Dates",
            "Actuals after the data date or forecasts before it",
            passed=len(invalid) <= th.invalid_dates_max,
            metric=float(len(invalid)),
            threshold_desc=f"count <= {th.invalid_dates_max}",
            count=len(invalid),
            eligible=len(tasks),
            offenders=invalid,
            note=None if dd else "no data date found; check skipped",
        )
    )

    # 10. Resources ----------------------------------------------------------
    pool10 = [
        a
        for a in incomplete
        if a.original_duration_hours > 0
        and not (th.exempt_milestones_from_resource_check and a.is_milestone)
    ]
    no_rsrc = [
        a
        for a in pool10
        if not sch.assignments_by_task.get(a.task_id) and not sch.expenses_by_task.get(a.task_id)
    ]
    pct10 = len(no_rsrc) / len(pool10) * 100 if pool10 else 0.0
    checks.append(
        _check(
            10,
            "Resources",
            "Incomplete tasks with duration but no resource assignment or expense",
            passed=len(no_rsrc) == 0,
            metric=pct10,
            threshold_desc="all tasks resourced (0 missing)",
            count=len(no_rsrc),
            eligible=len(pool10),
            offenders=no_rsrc,
        )
    )

    # 11. Missed tasks + 14. BEI --------------------------------------------
    bl_finish, bl_source = _baseline_finish_map(sch, projects)
    missed: list[Activity] = []
    should_have_finished = 0
    actually_finished_total = sum(1 for a in tasks if a.is_completed)
    if dd is not None:
        for a in tasks:
            bf = bl_finish.get(a.code)
            if bf is None or bf > dd:
                continue
            should_have_finished += 1
            actual = a.act_finish
            if actual is None or actual > bf:
                missed.append(a)
    pct11 = len(missed) / should_have_finished * 100 if should_have_finished else 0.0
    checks.append(
        _check(
            11,
            "Missed Tasks",
            "Tasks that missed their baseline finish (among those due by the data date)",
            passed=pct11 <= th.missed_tasks_pct_max,
            metric=pct11,
            threshold_desc=f"<= {th.missed_tasks_pct_max}%",
            count=len(missed),
            eligible=should_have_finished,
            offenders=missed,
            note=bl_source,
        )
    )

    # 12. Critical Path Test -------------------------------------------------
    cp_test = _critical_path_test(sch, projects, th)
    checks.append(cp_test)

    # 13. CPLI ---------------------------------------------------------------
    checks.append(_cpli(sch, projects, th, dd))

    # 14. BEI ----------------------------------------------------------------
    planned_to_finish = should_have_finished
    bei = actually_finished_total / planned_to_finish if planned_to_finish else None
    checks.append(
        _check(
            14,
            "Baseline Execution Index",
            "Tasks actually completed / tasks baselined to complete by the data date",
            passed=bei is None or bei >= th.bei_min,
            metric=round(bei, 3) if bei is not None else None,
            threshold_desc=f">= {th.bei_min}",
            count=actually_finished_total,
            eligible=planned_to_finish,
            offenders=[],
            note=bl_source,
        )
    )

    passed = sum(1 for c in checks if c["passed"])
    return {
        "data_date": dd,
        "activity_count": len(all_acts),
        "assessed_tasks": len(tasks),
        "incomplete_tasks": len(incomplete),
        "checks": checks,
        "summary": {
            "passed": passed,
            "failed": len(checks) - passed,
            "score_pct": round(passed / len(checks) * 100, 1),
        },
        "thresholds": asdict(th),
    }


def _critical_path_test(
    sch: Schedule, projects: list[Project], th: DcmaThresholds
) -> dict[str, Any]:
    """Add a large delay to a critical activity and confirm the finish moves."""
    base = compute_cpm(sch, projects)
    if base.project_finish is None:
        return _check(
            12,
            "Critical Path Test",
            "Delay a critical task; project finish must move",
            passed=False,
            metric=None,
            threshold_desc="finish moves with delay",
            count=0,
            eligible=0,
            offenders=[],
            note="no incomplete network to test",
        )
    critical = [
        tid
        for tid, tf in base.total_float_hours.items()
        if tf <= 0 and not sch.activities_by_id[tid].is_milestone
    ]
    if not critical:
        return _check(
            12,
            "Critical Path Test",
            "Delay a critical task; project finish must move",
            passed=False,
            metric=None,
            threshold_desc="finish moves with delay",
            count=0,
            eligible=0,
            offenders=[],
            note="no critical activities found",
        )
    victim_id = min(critical, key=lambda t: base.early_start[t])
    victim = sch.activities_by_id[victim_id]
    cal = sch.calendar_for(victim)
    delay_hours = th.critical_path_test_delay_days * (cal.day_hours if cal else 8.0)
    original_raw = victim.raw("remain_drtn_hr_cnt")
    try:
        victim.set("remain_drtn_hr_cnt", victim.remaining_duration_hours + delay_hours)
        delayed = compute_cpm(sch, projects)
    finally:
        victim.row[victim._table._field_index["remain_drtn_hr_cnt"]] = original_raw
    moved = delayed.project_finish is not None and delayed.project_finish > base.project_finish
    slip_days = None
    if delayed.project_finish and cal:
        slip_days = round(
            cal.work_hours_between(base.project_finish, delayed.project_finish) / cal.day_hours,
            1,
        )
    return _check(
        12,
        "Critical Path Test",
        f"Added {th.critical_path_test_delay_days:g} days to {victim.code}; "
        "project finish must slip",
        passed=bool(moved),
        metric=slip_days,
        threshold_desc="project finish moves",
        count=1 if moved else 0,
        eligible=1,
        offenders=[] if moved else [victim],
        note=f"test activity: {victim.code}; finish {base.project_finish} -> "
        f"{delayed.project_finish}",
    )


def _cpli(
    sch: Schedule, projects: list[Project], th: DcmaThresholds, dd: datetime | None
) -> dict[str, Any]:
    """Critical Path Length Index = (CPL + total float) / CPL, in working days."""
    proj = projects[0] if projects else None
    finishes = [
        a.finish for a in sch.activities_of(projects) if a.finish is not None and not a.is_loe
    ]
    project_finish = max(finishes, default=None)
    must_finish = proj.scd_end if proj else None
    if dd is None or project_finish is None:
        return _check(
            13,
            "CPLI",
            "Critical Path Length Index",
            passed=True,
            metric=None,
            threshold_desc=f">= {th.cpli_min}",
            count=0,
            eligible=0,
            offenders=[],
            note="cannot compute (missing data date or finish)",
        )
    cal = sch.default_calendar
    if proj is not None and proj.clndr_id is not None:
        cal = sch.calendars_by_id.get(proj.clndr_id, cal)
    if cal is None:
        cpl_days = max((project_finish - dd).days, 1)
        tf_days = (must_finish - project_finish).days if must_finish else 0
    else:
        cpl_days = max(cal.work_hours_between(dd, project_finish) / cal.day_hours, 0.1)
        tf_days = (
            cal.work_hours_between(project_finish, must_finish) / cal.day_hours
            if must_finish
            else 0.0
        )
    cpli = (cpl_days + tf_days) / cpl_days
    note = (
        None if must_finish else ("no must-finish-by date; project float taken as 0 so CPLI = 1.0")
    )
    return _check(
        13,
        "CPLI",
        "Critical Path Length Index (working days)",
        passed=cpli >= th.cpli_min,
        metric=round(cpli, 3),
        threshold_desc=f">= {th.cpli_min}",
        count=0,
        eligible=0,
        offenders=[],
        note=note,
    )
