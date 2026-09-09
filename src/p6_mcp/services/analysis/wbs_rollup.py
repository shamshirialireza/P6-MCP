"""WBS rollups: dates, counts, cost, and percent complete per subtree."""

from __future__ import annotations

from typing import Any

from p6_mcp.domain.project import Project
from p6_mcp.domain.schedule import Schedule
from p6_mcp.services.analysis.cost import activity_costs


def wbs_rollup(
    sch: Schedule, projects: list[Project], level: int | None = None
) -> list[dict[str, Any]]:
    """One row per WBS node with subtree aggregates (deterministic order)."""
    proj_ids = {p.proj_id for p in projects}
    nodes = [w for w in sch.wbs_nodes if w.proj_id in proj_ids]
    out: list[dict[str, Any]] = []
    for w in sorted(nodes, key=lambda x: (sch.wbs_level(x.wbs_id), x.num("seq_num"), x.wbs_id)):
        lvl = sch.wbs_level(w.wbs_id)
        if level is not None and lvl > level:
            continue
        subtree = sch.wbs_descendant_ids(w.wbs_id)
        acts = [a for wid in subtree for a in sch.activities_by_wbs.get(wid, [])]
        if not acts:
            out.append({
                "wbs_id": w.wbs_id, "path": sch.wbs_path(w.wbs_id), "level": lvl,
                "wbs_name": w.name, "activity_count": 0,
            })
            continue
        od = sum(a.original_duration_hours for a in acts)
        rd = sum(a.remaining_duration_hours for a in acts)
        weighted_pct = sum(
            a.original_duration_hours * a.percent_complete() for a in acts
        )
        costs = {"budgeted": 0.0, "actual": 0.0, "remaining": 0.0}
        qty = {"budgeted": 0.0, "actual": 0.0, "remaining": 0.0}
        for a in acts:
            c = activity_costs(sch, a)
            for k in costs:
                costs[k] += c[k]
            for x in sch.assignments_by_task.get(a.task_id, []):
                qty["budgeted"] += x.budgeted_qty
                qty["actual"] += x.actual_qty
                qty["remaining"] += x.remaining_qty
        floats = [
            sch.hours_to_days(a, a.total_float_hours)
            for a in acts
            if not a.is_completed and a.total_float_hours is not None
        ]
        out.append(
            {
                "wbs_id": w.wbs_id,
                "path": sch.wbs_path(w.wbs_id),
                "level": lvl,
                "wbs_name": w.name,
                "activity_count": len(acts),
                "status_counts": {
                    "completed": sum(1 for a in acts if a.is_completed),
                    "in_progress": sum(1 for a in acts if a.is_in_progress),
                    "not_started": sum(1 for a in acts if a.is_not_started),
                },
                "start": min((a.start for a in acts if a.start), default=None),
                "finish": max((a.finish for a in acts if a.finish), default=None),
                "actual_start": min((a.act_start for a in acts if a.act_start), default=None),
                "actual_finish": max((a.act_finish for a in acts if a.act_finish), default=None)
                if all(a.is_completed for a in acts)
                else None,
                "min_total_float_days": round(min(floats), 1) if floats else None,
                "percent_complete_duration": round((od - rd) / od * 100, 1) if od else 0.0,
                "percent_complete_weighted": round(weighted_pct / od, 1) if od else 0.0,
                "cost": {k: round(v, 2) for k, v in costs.items()},
                "qty": {k: round(v, 2) for k, v in qty.items()},
            }
        )
    return out
