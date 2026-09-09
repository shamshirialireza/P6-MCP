"""Critical path, near-critical, float paths, and float distribution.

Two methods are supported, mirroring P6's project setting:

* ``total_float``: total float ≤ threshold (project ``critical_drtn_hr_cnt``
  by default).
* ``longest_path``: activities with ``driving_path_flag = Y`` as computed by
  P6's last schedule run; falls back to tracing driving logic from the latest
  finish when the flag is absent.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from p6_mcp.domain.activity import Activity
from p6_mcp.domain.project import Project
from p6_mcp.domain.schedule import Schedule
from p6_mcp.exceptions import InvalidArgumentError


def _incomplete(activities: list[Activity], include_completed: bool) -> list[Activity]:
    if include_completed:
        return activities
    return [a for a in activities if not a.is_completed]


def critical_by_total_float(
    sch: Schedule,
    activities: list[Activity],
    float_threshold_hours: float = 0.0,
    include_completed: bool = False,
) -> list[Activity]:
    out = [
        a
        for a in _incomplete(activities, include_completed)
        if a.total_float_hours is not None and a.total_float_hours <= float_threshold_hours
    ]
    return sorted(out, key=lambda a: (a.start or a.finish or _MAXDT, a.code))


def critical_by_longest_path(
    sch: Schedule,
    activities: list[Activity],
    include_completed: bool = False,
) -> tuple[list[Activity], str]:
    """Longest-path activities; returns (activities, method_note)."""
    pool = _incomplete(activities, include_completed)
    flagged = [a for a in pool if a.driving_path_flag]
    if flagged:
        return (
            sorted(flagged, key=lambda a: (a.start or a.finish or _MAXDT, a.code)),
            "driving_path_flag from P6's last schedule run",
        )
    # Fallback: trace driving predecessors back from the latest-finishing task.
    if not pool:
        return [], "no incomplete activities"
    end = max(pool, key=lambda a: a.finish or _MINDT)
    chain = trace_driving_chain(sch, end, direction="backward")
    return chain, "traced driving predecessors from latest finish (no P6 flags present)"


def trace_driving_chain(
    sch: Schedule, start_from: Activity, direction: str = "backward"
) -> list[Activity]:
    """Follow driving relationships (zero relationship float heuristic)."""
    seen: set[int] = set()
    chain: list[Activity] = []
    current: Activity | None = start_from
    while current is not None and current.task_id not in seen:
        seen.add(current.task_id)
        chain.append(current)
        rels = (
            sch.predecessors_of.get(current.task_id, [])
            if direction == "backward"
            else sch.successors_of.get(current.task_id, [])
        )
        best: Activity | None = None
        best_gap = float("inf")
        for r in rels:
            other_id = r.pred_task_id if direction == "backward" else r.task_id
            other = sch.activities_by_id.get(other_id)
            if other is None or other.is_completed:
                continue
            gap = _relationship_gap(sch, r)
            if gap is not None and gap < best_gap:
                best_gap, best = gap, other
        if best is None or best_gap > 1e-6:
            break
        current = best
    if direction == "backward":
        chain.reverse()
    return chain


_MAXDT = datetime.max
_MINDT = datetime.min


def _relationship_gap(sch: Schedule, r: Any) -> float | None:
    """Working-hour slack across a relationship (0 ⇒ driving)."""
    pred = sch.activities_by_id.get(r.pred_task_id)
    succ = sch.activities_by_id.get(r.task_id)
    if pred is None or succ is None:
        return None
    t = r.pred_type
    p_start, p_finish = pred.start, pred.finish
    s_start, s_finish = succ.start, succ.finish
    if t == "PR_FS":
        a, b = p_finish, s_start
    elif t == "PR_SS":
        a, b = p_start, s_start
    elif t == "PR_FF":
        a, b = p_finish, s_finish
    else:  # PR_SF
        a, b = p_start, s_finish
    if a is None or b is None:
        return None
    cal = sch.calendar_for(succ)
    if cal is None:
        return None
    return cal.work_hours_between(a, b) - r.lag_hours


def get_critical_path(
    sch: Schedule,
    projects: list[Project],
    method: str = "total_float",
    float_threshold_hours: float | None = None,
    include_completed: bool = False,
) -> dict[str, Any]:
    """Critical activities per the requested method (or 'both')."""
    if method not in ("total_float", "longest_path", "both"):
        raise InvalidArgumentError(
            f"Unknown method {method!r}",
            hint="Use total_float, longest_path, or both.",
        )
    activities = sch.activities_of(projects)
    threshold = float_threshold_hours
    if threshold is None:
        threshold = max((p.critical_drtn_hr_cnt for p in projects), default=0.0)
    result: dict[str, Any] = {
        "method": method,
        "float_threshold_hours": threshold,
        "project_critical_path_setting": projects[0].critical_path_type_label if projects else None,
    }
    if method in ("total_float", "both"):
        result["total_float_critical"] = critical_by_total_float(
            sch, activities, threshold, include_completed
        )
    if method in ("longest_path", "both"):
        lp, note = critical_by_longest_path(sch, activities, include_completed)
        result["longest_path"] = lp
        result["longest_path_note"] = note
    return result


def get_near_critical(
    sch: Schedule, projects: list[Project], threshold_days: float = 5.0
) -> list[tuple[Activity, float]]:
    """Incomplete activities with 0 < total float ≤ threshold (calendar-aware days)."""
    out: list[tuple[Activity, float]] = []
    for a in sch.activities_of(projects):
        if a.is_completed or a.total_float_hours is None:
            continue
        days = sch.hours_to_days(a, a.total_float_hours)
        if days is not None and 0 < days <= threshold_days:
            out.append((a, days))
    out.sort(key=lambda t: (t[1], t[0].code))
    return out


def get_negative_float(sch: Schedule, projects: list[Project]) -> list[tuple[Activity, float]]:
    out: list[tuple[Activity, float]] = []
    for a in sch.activities_of(projects):
        if a.is_completed or a.total_float_hours is None:
            continue
        if a.total_float_hours < 0:
            out.append((a, sch.hours_to_days(a, a.total_float_hours) or 0.0))
    out.sort(key=lambda t: (t[1], t[0].code))
    return out


def get_float_paths(sch: Schedule, projects: list[Project], max_paths: int = 5) -> dict[str, Any]:
    """Group by P6 multiple-float-path fields, else bucket by float value."""
    activities = [a for a in sch.activities_of(projects) if not a.is_completed]
    with_fp = [a for a in activities if a.f("float_path") is not None]
    if with_fp:
        paths: dict[int, list[Activity]] = {}
        for a in with_fp:
            paths.setdefault(int(a.f("float_path")), []).append(a)
        ordered = dict(sorted(paths.items())[:max_paths])
        for members in ordered.values():
            members.sort(key=lambda a: (a.num("float_path_order"), a.code))
        return {"source": "p6_float_path_fields", "paths": ordered}
    # Fallback: rank distinct float values ascending.
    buckets: dict[float, list[Activity]] = {}
    for a in activities:
        tf = a.total_float_hours
        if tf is not None:
            buckets.setdefault(tf, []).append(a)
    ordered_paths = {
        i + 1: sorted(members, key=lambda a: (a.start or _MAXDT, a.code))
        for i, (_tf, members) in enumerate(sorted(buckets.items())[:max_paths])
    }
    return {"source": "grouped_by_total_float (no float_path data)", "paths": ordered_paths}


def get_float_distribution(
    sch: Schedule, projects: list[Project], bins: list[float] | None = None
) -> dict[str, Any]:
    """Histogram of total float in days over incomplete activities."""
    edges = bins or [-10.0, 0.0, 5.0, 10.0, 22.0, 44.0, 88.0]
    counts = [0] * (len(edges) + 1)
    values: list[float] = []
    for a in sch.activities_of(projects):
        if a.is_completed:
            continue
        days = sch.hours_to_days(a, a.total_float_hours)
        if days is None:
            continue
        values.append(days)
        placed = False
        for i, edge in enumerate(edges):
            if days <= edge:
                counts[i] += 1
                placed = True
                break
        if not placed:
            counts[-1] += 1
    labels = []
    prev: float | None = None
    for edge in edges:
        labels.append(f"<= {edge:g}d" if prev is None else f"({prev:g}, {edge:g}]d")
        prev = edge
    labels.append(f"> {edges[-1]:g}d")
    stats: dict[str, Any] = {"count": len(values)}
    if values:
        values.sort()
        stats.update(
            min=round(values[0], 2),
            max=round(values[-1], 2),
            median=round(values[len(values) // 2], 2),
            mean=round(sum(values) / len(values), 2),
        )
    return {"bins": [{"range": lab, "count": c} for lab, c in zip(labels, counts)], "stats": stats}
