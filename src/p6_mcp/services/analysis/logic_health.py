"""Network logic health: open ends, dangling, redundancy, circularity,
out-of-sequence progress, leads/lags, relationship mix."""

from __future__ import annotations

from typing import Any

from p6_mcp.domain.activity import SUMMARY_LIKE_TYPES, Activity
from p6_mcp.domain.project import Project
from p6_mcp.domain.schedule import Schedule


def _eligible(a: Activity) -> bool:
    """Activities logic checks apply to (skip LOE/WBS summaries)."""
    return a.task_type not in SUMMARY_LIKE_TYPES


def open_ends(sch: Schedule, activities: list[Activity]) -> dict[str, list[Activity]]:
    """Activities with no predecessors / no successors (excluding LOE/WBS)."""
    no_preds = [a for a in activities if _eligible(a) and a.task_id not in sch.predecessors_of]
    no_succs = [a for a in activities if _eligible(a) and a.task_id not in sch.successors_of]
    return {"no_predecessors": no_preds, "no_successors": no_succs}


def dangling(sch: Schedule, activities: list[Activity]) -> dict[str, list[Activity]]:
    """SS-only successors (finish dangles) and FF-only predecessors (start dangles)."""
    finish_dangles: list[Activity] = []
    start_dangles: list[Activity] = []
    for a in activities:
        if not _eligible(a):
            continue
        succs = sch.successors_of.get(a.task_id, [])
        preds = sch.predecessors_of.get(a.task_id, [])
        if succs and all(r.pred_type == "PR_SS" for r in succs):
            finish_dangles.append(a)
        if preds and all(r.pred_type == "PR_FF" for r in preds):
            start_dangles.append(a)
    return {"finish_dangles": finish_dangles, "start_dangles": start_dangles}


def redundant_relationships(sch: Schedule, activities: list[Activity]) -> list[dict[str, Any]]:
    """FS links whose predecessor also reaches the successor via another FS path."""
    ids = {a.task_id for a in activities}
    succ_map: dict[int, set[int]] = {}
    for r in sch.relationships:
        if r.pred_type == "PR_FS" and r.pred_task_id in ids and r.task_id in ids:
            succ_map.setdefault(r.pred_task_id, set()).add(r.task_id)
    redundant: list[dict[str, Any]] = []
    for pred_id, direct in succ_map.items():
        if len(direct) < 2:
            continue
        for target in direct:
            # Is target reachable from pred via another direct successor?
            stack = [s for s in direct if s != target]
            seen: set[int] = set()
            found = False
            while stack and not found:
                cur = stack.pop()
                if cur in seen:
                    continue
                seen.add(cur)
                for nxt in succ_map.get(cur, ()):
                    if nxt == target:
                        found = True
                        break
                    stack.append(nxt)
            if found:
                p = sch.activities_by_id.get(pred_id)
                s = sch.activities_by_id.get(target)
                redundant.append(
                    {
                        "predecessor": p.code if p else pred_id,
                        "successor": s.code if s else target,
                        "reason": "already linked through an intermediate FS path",
                    }
                )
    return sorted(redundant, key=lambda d: (str(d["predecessor"]), str(d["successor"])))


def circular_logic(sch: Schedule, activities: list[Activity]) -> list[list[str]]:
    """Cycles in the relationship graph (P6 prevents these, but merged/edited
    files can contain them). Returns up to 10 cycles as task_code lists."""
    ids = {a.task_id for a in activities}
    graph: dict[int, list[int]] = {}
    for r in sch.relationships:
        if r.pred_task_id in ids and r.task_id in ids:
            graph.setdefault(r.pred_task_id, []).append(r.task_id)
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[int, int] = dict.fromkeys(ids, WHITE)
    cycles: list[list[str]] = []
    stack_path: list[int] = []

    def dfs(node: int) -> None:
        if len(cycles) >= 10:
            return
        color[node] = GRAY
        stack_path.append(node)
        for nxt in graph.get(node, ()):
            if color.get(nxt, BLACK) == GRAY:
                i = stack_path.index(nxt)
                cycle = [*stack_path[i:], nxt]
                cycles.append(
                    [sch.activities_by_id[t].code for t in cycle if t in sch.activities_by_id]
                )
            elif color.get(nxt) == WHITE:
                dfs(nxt)
        stack_path.pop()
        color[node] = BLACK

    import sys

    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(max(old_limit, len(ids) + 1000))
    try:
        for tid in sorted(ids):
            if color[tid] == WHITE:
                dfs(tid)
    finally:
        sys.setrecursionlimit(old_limit)
    return cycles


def out_of_sequence(sch: Schedule, activities: list[Activity]) -> list[dict[str, Any]]:
    """Successors that started before their predecessor requirement was met."""
    ids = {a.task_id for a in activities}
    issues: list[dict[str, Any]] = []
    for r in sch.relationships:
        if r.task_id not in ids:
            continue
        pred = sch.activities_by_id.get(r.pred_task_id)
        succ = sch.activities_by_id.get(r.task_id)
        if pred is None or succ is None or succ.act_start is None:
            continue
        t = r.pred_type
        violated = False
        if t == "PR_FS":
            violated = pred.act_finish is None or pred.act_finish > succ.act_start
        elif t == "PR_SS":
            violated = pred.act_start is None or pred.act_start > succ.act_start
        elif t == "PR_FF" and succ.act_finish is not None:
            violated = pred.act_finish is None or pred.act_finish > succ.act_finish
        elif t == "PR_SF" and succ.act_finish is not None:
            violated = pred.act_start is None or pred.act_start > succ.act_finish
        if violated:
            issues.append(
                {
                    "successor": succ.code,
                    "successor_name": succ.name,
                    "predecessor": pred.code,
                    "type": r.short_type,
                    "detail": f"{succ.code} started {succ.act_start:%Y-%m-%d} but "
                    f"{r.short_type} predecessor {pred.code} is not satisfied",
                }
            )
    return sorted(issues, key=lambda d: (str(d["successor"]), str(d["predecessor"])))


def relationship_mix(sch: Schedule, activities: list[Activity]) -> dict[str, Any]:
    ids = {a.task_id for a in activities}
    rels = [r for r in sch.relationships if r.task_id in ids or r.pred_task_id in ids]
    counts = {"FS": 0, "SS": 0, "FF": 0, "SF": 0}
    leads, lags, negative_lag_hours = 0, 0, 0.0
    cross_project = 0
    lag_values: list[float] = []
    for r in rels:
        counts[r.short_type] = counts.get(r.short_type, 0) + 1
        if r.is_lead:
            leads += 1
            negative_lag_hours += r.lag_hours
        elif r.is_lag:
            lags += 1
            lag_values.append(r.lag_hours)
        if r.crosses_projects:
            cross_project += 1
    total = len(rels)
    return {
        "total_relationships": total,
        "counts": counts,
        "percentages": {k: round(v / total * 100, 1) if total else 0.0 for k, v in counts.items()},
        "leads": leads,
        "lags": lags,
        "lag_hours_distribution": sorted(lag_values),
        "cross_project_relationships": cross_project,
    }


def analyze_logic_health(sch: Schedule, projects: list[Project]) -> dict[str, Any]:
    """The full logic-health bundle."""
    activities = sch.activities_of(projects)
    incomplete = [a for a in activities if not a.is_completed]
    oe = open_ends(sch, incomplete)
    dang = dangling(sch, incomplete)
    return {
        "activity_count": len(activities),
        "incomplete_count": len(incomplete),
        "open_ends": oe,
        "dangling": dang,
        "redundant": redundant_relationships(sch, activities),
        "circular": circular_logic(sch, activities),
        "out_of_sequence": out_of_sequence(sch, activities),
        "relationship_mix": relationship_mix(sch, activities),
    }
