"""Earned value: PV time-phased to the data date, EV/AC, indices, forecasts.

PV is the cumulative *time-phased* planned cost through the data date (never
the total budget). EV honors each activity's ``complete_pct_type`` by default
(``ev_method='from_p6_settings'``). Baseline dates are used for PV when a
linked baseline project exists in the file; otherwise planned (target) dates
are used and noted.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from p6_mcp.domain.activity import Activity
from p6_mcp.domain.project import Project
from p6_mcp.domain.schedule import Schedule
from p6_mcp.exceptions import InvalidArgumentError
from p6_mcp.services.analysis.cost import activity_costs
from p6_mcp.services.analysis.time_phasing import merge_series, series_to_rows, spread

EV_METHODS = ("from_p6_settings", "physical", "duration", "units", "activity_pct")
EAC_METHODS = ("cpi", "spi_cpi", "remaining", "bac_ac_plus_etc")


def _pct(a: Activity, method: str) -> float:
    if method == "from_p6_settings" or method == "activity_pct":
        return a.percent_complete() / 100.0
    if a.is_completed:
        return 1.0
    if a.is_not_started:
        return 0.0
    if method == "physical":
        return a.physical_pct / 100.0
    if method == "units":
        act = a.num("act_work_qty") + a.num("act_equip_qty")
        rem = a.num("remain_work_qty") + a.num("remain_equip_qty")
        total = act + rem
        return act / total if total else 0.0
    if method == "duration":
        od = a.original_duration_hours
        return max(0.0, min(1.0, (od - a.remaining_duration_hours) / od)) if od else 0.0
    raise InvalidArgumentError(f"Unknown ev_method {method!r}", hint=f"Use {EV_METHODS}")


def _baseline_activity_map(
    sch: Schedule, projects: list[Project]
) -> tuple[dict[str, Activity], str | None]:
    bl_ids: set[int] = set()
    for p in projects:
        if p.sum_base_proj_id is not None:
            bl_ids.add(p.sum_base_proj_id)
    for bp in sch.baseline_projects:
        if bp.orig_proj_id in {p.proj_id for p in projects}:
            bl_ids.add(bp.proj_id)
    if not bl_ids:
        return {}, "no baseline project in file; planned (target) dates used for PV"
    return {a.code: a for a in sch.activities if a.proj_id in bl_ids}, None


def earned_value(
    sch: Schedule,
    projects: list[Project],
    as_of: datetime | None = None,
    ev_method: str = "from_p6_settings",
    eac_method: str = "cpi",
    time_phased: bool = True,
    period: str = "month",
) -> dict[str, Any]:
    """Full EVM computation for the selected projects."""
    if ev_method not in EV_METHODS:
        raise InvalidArgumentError(f"Unknown ev_method {ev_method!r}", hint=f"Use {EV_METHODS}")
    if eac_method not in EAC_METHODS:
        raise InvalidArgumentError(f"Unknown eac_method {eac_method!r}", hint=f"Use {EAC_METHODS}")
    dd = as_of or sch.data_date(projects[0] if projects else None)
    bl_map, bl_note = _baseline_activity_map(sch, projects)

    bac = ev = ac = pv = 0.0
    etc_remaining = 0.0
    pv_series: dict[str, float] = {}
    by_wbs: dict[str, dict[str, float]] = {}
    for a in sch.activities_of(projects):
        costs = activity_costs(sch, a)
        a_bac = costs["budgeted"]
        a_ac = costs["actual"]
        a_ev = a_bac * _pct(a, ev_method)
        etc_remaining += costs["remaining"]
        bl = bl_map.get(a.code)
        pv_start = (bl.planned_start or bl.start) if bl else (a.planned_start or a.start)
        pv_finish = (bl.planned_finish or bl.finish) if bl else (a.planned_finish or a.finish)
        bl_bac = a_bac
        if bl is not None:
            bl_costs = activity_costs(sch, bl)
            if bl_costs["budgeted"] > 0:
                bl_bac = bl_costs["budgeted"]
        a_pv = 0.0
        cal = sch.calendar_for(a)
        if pv_start and pv_finish and cal and bl_bac:
            if dd is None or pv_finish <= dd:
                a_pv = bl_bac
            elif pv_start >= dd:
                a_pv = 0.0
            else:
                done = cal.work_hours_between(pv_start, dd)
                total = cal.work_hours_between(pv_start, pv_finish)
                a_pv = bl_bac * (done / total if total > 0 else 1.0)
            if time_phased:
                merge_series(pv_series, spread(cal, pv_start, pv_finish, bl_bac, period))
        bac += a_bac
        ev += a_ev
        ac += a_ac
        pv += a_pv
        wkey = sch.wbs_path(a.wbs_id) or "(no WBS)"
        node = by_wbs.setdefault(wkey, {"bac": 0.0, "pv": 0.0, "ev": 0.0, "ac": 0.0})
        node["bac"] += a_bac
        node["pv"] += a_pv
        node["ev"] += a_ev
        node["ac"] += a_ac

    cpi = ev / ac if ac else None
    spi = ev / pv if pv else None
    etc, eac = _forecast(eac_method, bac, ev, ac, cpi, spi, etc_remaining)
    out: dict[str, Any] = {
        "as_of": (dd.isoformat(sep=" ") if dd else None),
        "ev_method": ev_method,
        "eac_method": eac_method,
        "metrics": {
            "BAC": round(bac, 2),
            "PV": round(pv, 2),
            "EV": round(ev, 2),
            "AC": round(ac, 2),
            "CV": round(ev - ac, 2),
            "SV": round(ev - pv, 2),
            "CPI": round(cpi, 3) if cpi is not None else None,
            "SPI": round(spi, 3) if spi is not None else None,
            "ETC": round(etc, 2) if etc is not None else None,
            "EAC": round(eac, 2) if eac is not None else None,
            "VAC": round(bac - eac, 2) if eac is not None else None,
            "TCPI": round((bac - ev) / (bac - ac), 3) if bac - ac else None,
            "percent_complete": round(ev / bac * 100, 1) if bac else None,
            "percent_spent": round(ac / bac * 100, 1) if bac else None,
        },
        "eac_all_methods": {
            m: round(v, 2)
            for m in EAC_METHODS
            if (v := _forecast(m, bac, ev, ac, cpi, spi, etc_remaining)[1]) is not None
        },
        "by_wbs": [
            {
                "wbs": k,
                **{m: round(v, 2) for m, v in vals.items()},
                "cpi": round(vals["ev"] / vals["ac"], 3) if vals["ac"] else None,
                "spi": round(vals["ev"] / vals["pv"], 3) if vals["pv"] else None,
            }
            for k, vals in sorted(by_wbs.items())
        ],
    }
    if bl_note:
        out["note"] = bl_note
    if time_phased:
        out["pv_curve"] = series_to_rows({"pv": pv_series}, cumulative_keys=("pv",))
    return out


def _forecast(
    method: str,
    bac: float,
    ev: float,
    ac: float,
    cpi: float | None,
    spi: float | None,
    etc_remaining: float,
) -> tuple[float | None, float | None]:
    """(ETC, EAC) per the requested formula."""
    if method == "cpi":
        if not cpi:
            return None, None
        eac = bac / cpi
        return eac - ac, eac
    if method == "spi_cpi":
        if not cpi or not spi:
            return None, None
        etc = (bac - ev) / (cpi * spi)
        return etc, ac + etc
    if method == "remaining":
        etc = bac - ev
        return etc, ac + etc
    # bac_ac_plus_etc: bottom-up using the schedule's own remaining cost
    return etc_remaining, ac + etc_remaining
