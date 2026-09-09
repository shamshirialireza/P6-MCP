"""Time-phased resource utilization, histograms, and over-allocation."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from p6_mcp.domain.project import Project
from p6_mcp.domain.resource import Assignment, Resource
from p6_mcp.domain.schedule import Schedule
from p6_mcp.services.analysis.time_phasing import (
    iter_periods,
    merge_series,
    parse_curve,
    period_label,
    spread,
)


def _assignment_curve(sch: Schedule, x: Assignment) -> list[float] | None:
    if x.curve_id is None:
        return None
    t = sch.table("RSRCCURVDATA")
    for d in t.iter_dicts(typed=False):
        try:
            if int(d.get("curv_id") or 0) == x.curve_id:
                return parse_curve(d.get("curv_data") or "")
        except ValueError:
            continue
    return None


def utilization(
    sch: Schedule,
    projects: list[Project],
    period: str = "week",
    start: datetime | None = None,
    end: datetime | None = None,
    rsrc_ids: list[int] | None = None,
    use_curves: bool = True,
    compare_to: str | None = "max_units",
) -> dict[str, Any]:
    """Planned/actual/remaining qty & cost per resource per period, with
    per-period over-allocation flags against RSRCRATE max units × calendar hours."""
    proj_ids = {p.proj_id for p in projects}
    dd = sch.data_date(projects[0] if projects else None)
    per_resource: dict[int, dict[str, dict[str, float]]] = {}
    for x in sch.assignments:
        if x.proj_id not in proj_ids or x.rsrc_id is None:
            continue
        if rsrc_ids and x.rsrc_id not in rsrc_ids:
            continue
        act = sch.activities_by_id.get(x.task_id)
        if act is None:
            continue
        rsrc = sch.resources_by_id.get(x.rsrc_id)
        cal = (
            sch.calendars_by_id.get(rsrc.clndr_id)
            if rsrc and rsrc.clndr_id
            else None
        ) or sch.calendar_for(act)
        if cal is None:
            continue
        curve = _assignment_curve(sch, x) if use_curves else None
        bucket = per_resource.setdefault(
            x.rsrc_id,
            {k: {} for k in (
                "planned_qty", "actual_qty", "remaining_qty",
                "planned_cost", "actual_cost", "remaining_cost",
            )},
        )
        ps, pf = x.planned_start, x.planned_finish
        if ps and pf:
            merge_series(bucket["planned_qty"], spread(cal, ps, pf, x.budgeted_qty, period, curve))
            merge_series(bucket["planned_cost"], spread(cal, ps, pf, x.budgeted_cost, period, curve))
        a_start = x.f("act_start_date")
        a_end = x.f("act_end_date") or dd
        if a_start and a_end and x.actual_qty:
            merge_series(bucket["actual_qty"], spread(cal, a_start, a_end, x.actual_qty, period))
            merge_series(bucket["actual_cost"], spread(cal, a_start, a_end, x.actual_cost, period))
        r_start = x.f("restart_date") or (dd if a_start else ps)
        r_finish = x.f("reend_date") or x.finish
        if r_start and r_finish and x.remaining_qty:
            merge_series(
                bucket["remaining_qty"], spread(cal, r_start, r_finish, x.remaining_qty, period, curve)
            )
            merge_series(
                bucket["remaining_cost"], spread(cal, r_start, r_finish, x.remaining_cost, period, curve)
            )

    resources_out: list[dict[str, Any]] = []
    for rid in sorted(per_resource):
        rsrc = sch.resources_by_id.get(rid)
        series = per_resource[rid]
        labels = sorted({lab for m in series.values() for lab in m})
        if start:
            labels = [
                lab for lab in labels
                if lab >= period_label(start.date(), period)
            ]
        if end:
            labels = [lab for lab in labels if lab <= period_label(end.date(), period)]
        limit_series = _limits(sch, rsrc, labels, period, compare_to)
        rows = []
        for lab in labels:
            demand = series["remaining_qty"].get(lab, 0.0) + series["actual_qty"].get(lab, 0.0)
            limit = limit_series.get(lab)
            rows.append(
                {
                    "period": lab,
                    **{k: round(series[k].get(lab, 0.0), 2) for k in series},
                    "limit_qty": round(limit, 2) if limit is not None else None,
                    "overallocated": bool(limit is not None and demand > limit + 1e-6),
                }
            )
        resources_out.append(
            {
                "rsrc_id": rid,
                "resource": rsrc.name if rsrc else str(rid),
                "rsrc_type": rsrc.type_label if rsrc else None,
                "periods": rows,
                "totals": {k: round(sum(v.values()), 2) for k, v in series.items()},
                "overallocated_periods": sum(1 for r in rows if r["overallocated"]),
            }
        )
    return {
        "period": period,
        "compare_to": compare_to,
        "use_curves": use_curves,
        "resources": resources_out,
    }


def _limits(
    sch: Schedule,
    rsrc: Resource | None,
    labels: list[str],
    period: str,
    compare_to: str | None,
) -> dict[str, float]:
    """Per-period availability = max_qty_per_hr × working hours in period."""
    if rsrc is None or compare_to is None or not labels:
        return {}
    rates = sch.rates_by_rsrc.get(rsrc.rsrc_id, [])
    max_per_hr = None
    for r in rates:
        v = r.get("max_qty_per_hr")
        if v is not None:
            max_per_hr = float(v)
    if max_per_hr is None:
        max_per_hr = float(rsrc.f("def_qty_per_hr") or 0) or None
    if max_per_hr is None:
        return {}
    cal = (
        sch.calendars_by_id.get(rsrc.clndr_id)
        if rsrc.clndr_id
        else None
    ) or sch.default_calendar
    if cal is None:
        return {}
    out: dict[str, float] = {}
    lo = min(labels)
    hi = max(labels)
    span_start = None
    for a in sch.activities:
        if a.start:
            span_start = min(span_start or a.start, a.start)
    anchor = span_start or datetime(2020, 1, 1)
    d = anchor.date()
    for p_start, p_end in iter_periods(d, d.replace(year=d.year + 15), period):
        lab = period_label(p_start, period)
        if lab < lo:
            continue
        if lab > hi:
            break
        hours = cal.work_hours_between(
            datetime.combine(p_start, datetime.min.time()),
            datetime.combine(p_end, datetime.min.time()),
        )
        out[lab] = hours * max_per_hr
    return out


def leveling_report(sch: Schedule, projects: list[Project], period: str = "week"
                    ) -> dict[str, Any]:
    """Peaks and over-limit periods per resource."""
    util = utilization(sch, projects, period=period)
    out = []
    for r in util["resources"]:
        rows = r["periods"]
        if not rows:
            continue
        peak = max(rows, key=lambda x: x["remaining_qty"] + x["actual_qty"])
        out.append(
            {
                "resource": r["resource"],
                "rsrc_id": r["rsrc_id"],
                "peak_period": peak["period"],
                "peak_qty": round(peak["remaining_qty"] + peak["actual_qty"], 2),
                "overallocated_periods": [
                    {"period": x["period"],
                     "demand": round(x["remaining_qty"] + x["actual_qty"], 2),
                     "limit": x["limit_qty"]}
                    for x in rows if x["overallocated"]
                ],
            }
        )
    return {"period": period, "resources": out}
