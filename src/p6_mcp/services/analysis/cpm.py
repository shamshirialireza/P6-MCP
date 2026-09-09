"""Independent CPM forward/backward pass over the parsed network.

Purpose: validate the stored P6 dates and float, and re-schedule after edits.
Documented limitations vs the P6 engine (see docs/concepts/critical-path.md):
retained logic only (no progress override), no resource leveling, no ALAP
repositioning, lag uses the predecessor's calendar on the forward pass and the
successor's on the backward pass.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
from typing import Any

from p6_mcp.domain.activity import Activity
from p6_mcp.domain.calendar import Calendar
from p6_mcp.domain.project import Project
from p6_mcp.domain.schedule import Schedule


class CpmResult:
    """Computed dates/float per task_id plus a comparison to stored values."""

    def __init__(self) -> None:
        self.early_start: dict[int, datetime] = {}
        self.early_finish: dict[int, datetime] = {}
        self.late_start: dict[int, datetime] = {}
        self.late_finish: dict[int, datetime] = {}
        self.total_float_hours: dict[int, float] = {}
        self.notes: list[str] = []
        self.project_finish: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_finish": self.project_finish,
            "computed_count": len(self.early_start),
            "notes": self.notes,
        }


def _fallback_calendar(sch: Schedule) -> Calendar | None:
    return sch.default_calendar


def compute_cpm(
    sch: Schedule,
    projects: list[Project],
    data_date: datetime | None = None,
) -> CpmResult:
    """Run the forward/backward pass for the given projects."""
    res = CpmResult()
    activities = sch.activities_of(projects)
    dd = data_date or sch.data_date(projects[0] if projects else None)
    if dd is None:
        dd = min(
            (a.start for a in activities if a.start is not None),
            default=datetime(2000, 1, 3, 8),
        )
        res.notes.append("no data date found; using earliest activity start")

    incomplete = {a.task_id: a for a in activities if not a.is_completed}
    all_ids = {a.task_id for a in activities}
    rels = [r for r in sch.relationships if r.task_id in all_ids and r.pred_task_id in all_ids]
    preds_of: dict[int, list[Any]] = {}
    succs_of: dict[int, list[Any]] = {}
    for r in rels:
        preds_of.setdefault(r.task_id, []).append(r)
        succs_of.setdefault(r.pred_task_id, []).append(r)

    def cal_of(a: Activity) -> Calendar | None:
        return sch.calendar_for(a) or _fallback_calendar(sch)

    # ---- topological order over incomplete tasks (cycles broken with a note)
    indeg = dict.fromkeys(incomplete, 0)
    for r in rels:
        if r.task_id in incomplete and r.pred_task_id in incomplete:
            indeg[r.task_id] += 1
    queue = deque(sorted(t for t, d in indeg.items() if d == 0))
    order: list[int] = []
    while queue:
        t = queue.popleft()
        order.append(t)
        for r in succs_of.get(t, ()):
            if r.task_id in incomplete:
                indeg[r.task_id] -= 1
                if indeg[r.task_id] == 0:
                    queue.append(r.task_id)
    if len(order) < len(incomplete):
        res.notes.append(
            f"circular logic: {len(incomplete) - len(order)} activities scheduled "
            "in arbitrary order"
        )
        order.extend(sorted(set(incomplete) - set(order)))

    ES, EF = res.early_start, res.early_finish

    def pred_points(tid: int) -> tuple[datetime | None, datetime | None]:
        """(start, finish) reference points of a predecessor for the forward pass."""
        a = sch.activities_by_id[tid]
        if a.is_completed:
            return a.act_start, a.act_finish
        if tid in ES:
            s = a.act_start or ES[tid]
            return s, EF[tid]
        return None, None

    # ---- forward pass
    for tid in order:
        a = incomplete[tid]
        cal = cal_of(a)
        if cal is None:
            continue
        dur = a.remaining_duration_hours
        if a.is_in_progress:
            es = cal.next_work_time(dd)
        else:
            es = cal.next_work_time(dd)
            raw_candidate: datetime | None = None
            for r in preds_of.get(tid, ()):
                p_start, p_finish = pred_points(r.pred_task_id)
                pred_act = sch.activities_by_id.get(r.pred_task_id)
                lag_cal = (cal_of(pred_act) if pred_act else cal) or cal
                t = r.pred_type
                cand: datetime | None = None
                if t == "PR_FS" and p_finish:
                    cand = lag_cal.add_work_hours(p_finish, r.lag_hours)
                elif t == "PR_SS" and p_start:
                    cand = lag_cal.add_work_hours(p_start, r.lag_hours)
                elif t == "PR_FF" and p_finish:
                    ef_req = lag_cal.add_work_hours(p_finish, r.lag_hours)
                    cand = cal.add_work_hours(ef_req, -dur)
                elif t == "PR_SF" and p_start:
                    ef_req = lag_cal.add_work_hours(p_start, r.lag_hours)
                    cand = cal.add_work_hours(ef_req, -dur)
                if cand is not None and cand > es:
                    es = cand
                    raw_candidate = cand
            if a.task_type == "TT_FinMile" and raw_candidate is not None:
                # A finish milestone occupies its predecessor's finish instant
                # (P6 shows it at end-of-shift, not next-day 08:00).
                es = cal.prev_work_time(raw_candidate)
            else:
                es = cal.next_work_time(es)
            # early constraints
            ct, cd = a.cstr_type, a.cstr_date
            if ct in ("CS_MSOA", "CS_MSO", "CS_MANDSTART") and cd and cd > es:
                es = cal.next_work_time(cd)
            if ct in ("CS_MEOA", "CS_MEO") and cd:
                es_from_fin = cal.add_work_hours(cd, -dur)
                if es_from_fin > es:
                    es = es_from_fin
            if ct == "CS_MANDFIN" and cd:
                es = cal.add_work_hours(cd, -dur)
        ES[tid] = es
        EF[tid] = cal.add_work_hours(es, dur)
        if a.is_loe:
            # LOE spans its linked work: finish is bound by FF/SF predecessors.
            ff_bound: datetime | None = None
            for r in preds_of.get(tid, ()):
                p_start, p_finish = pred_points(r.pred_task_id)
                ref = p_finish if r.pred_type in ("PR_FF", "PR_FS") else p_start
                if r.pred_type in ("PR_FF", "PR_SF") and ref is not None:
                    cand = cal.add_work_hours(ref, r.lag_hours)
                    if ff_bound is None or cand > ff_bound:
                        ff_bound = cand
            if ff_bound is not None:
                EF[tid] = max(es, ff_bound)

    if not EF:
        return res
    non_loe_ef = [ef for t, ef in EF.items() if not incomplete[t].is_loe]
    project_finish = max(non_loe_ef or EF.values())
    scd = max((p.scd_end for p in projects if p.scd_end), default=None)
    res.project_finish = project_finish
    horizon = max(project_finish, scd) if scd else project_finish

    LS, LF = res.late_start, res.late_finish

    # ---- backward pass
    for tid in reversed(order):
        a = incomplete[tid]
        cal = cal_of(a)
        if cal is None:
            continue
        dur = a.remaining_duration_hours
        lf_bound = horizon
        ls_bound: datetime | None = None
        for r in succs_of.get(tid, ()):
            s_id = r.task_id
            succ = sch.activities_by_id.get(s_id)
            if succ is None or succ.is_completed or s_id not in LS:
                continue
            lag_cal = cal_of(succ) or cal
            t = r.pred_type
            if t == "PR_FS":
                cand = lag_cal.add_work_hours(LS[s_id], -r.lag_hours)
                lf_bound = min(lf_bound, cand)
            elif t == "PR_FF":
                cand = lag_cal.add_work_hours(LF[s_id], -r.lag_hours)
                lf_bound = min(lf_bound, cand)
            elif t == "PR_SS":
                cand = lag_cal.add_work_hours(LS[s_id], -r.lag_hours)
                ls_bound = cand if ls_bound is None else min(ls_bound, cand)
            else:  # PR_SF
                cand = lag_cal.add_work_hours(LF[s_id], -r.lag_hours)
                ls_bound = cand if ls_bound is None else min(ls_bound, cand)
        # late constraints
        ct, cd = a.cstr_type, a.cstr_date
        if ct in ("CS_MEOB", "CS_MEO", "CS_MANDFIN") and cd:
            lf_bound = min(lf_bound, cd)
        if ct in ("CS_MSOB", "CS_MSO", "CS_MANDSTART") and cd:
            ls_bound = cd if ls_bound is None else min(ls_bound, cd)
        ls = cal.add_work_hours(lf_bound, -dur)
        if ls_bound is not None and ls_bound < ls:
            ls = ls_bound
        LS[tid] = ls
        LF[tid] = cal.add_work_hours(ls, dur)
        res.total_float_hours[tid] = round(cal.work_hours_between(ES[tid], ls), 4)
    return res


def compare_to_stored(
    sch: Schedule, res: CpmResult, tolerance_hours: float = 1.0
) -> dict[str, Any]:
    """Diff computed vs stored dates/float; returns summary + top deviations."""
    diffs: list[dict[str, Any]] = []
    matched = 0
    for tid, es in res.early_start.items():
        a = sch.activities_by_id.get(tid)
        if a is None:
            continue
        stored_es, stored_ef = a.early_start, a.early_finish
        stored_tf = a.total_float_hours
        cal = sch.calendar_for(a)
        dev = 0.0
        details: dict[str, Any] = {}
        if stored_es is not None and cal is not None:
            d = abs(cal.work_hours_between(stored_es, es))
            if d > tolerance_hours:
                details["early_start"] = {
                    "stored": stored_es,
                    "computed": es,
                    "deviation_hours": round(d, 1),
                }
                dev = max(dev, d)
        if stored_ef is not None and cal is not None:
            d = abs(cal.work_hours_between(stored_ef, res.early_finish[tid]))
            if d > tolerance_hours:
                details["early_finish"] = {
                    "stored": stored_ef,
                    "computed": res.early_finish[tid],
                    "deviation_hours": round(d, 1),
                }
                dev = max(dev, d)
        tf = res.total_float_hours.get(tid)
        if stored_tf is not None and tf is not None and abs(stored_tf - tf) > tolerance_hours:
            details["total_float"] = {"stored_hours": stored_tf, "computed_hours": tf}
            dev = max(dev, abs(stored_tf - tf))
        if details:
            diffs.append(
                {
                    "task_code": a.code,
                    "task_name": a.name,
                    "max_deviation_hours": round(dev, 1),
                    **details,
                }
            )
        else:
            matched += 1
    diffs.sort(key=lambda d: -float(d["max_deviation_hours"]))
    return {
        "computed": len(res.early_start),
        "matching_stored": matched,
        "deviating": len(diffs),
        "tolerance_hours": tolerance_hours,
        "top_deviations": diffs[:50],
    }
