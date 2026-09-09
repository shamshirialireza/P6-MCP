"""Current-vs-baseline comparison (baseline in the same file or a second file)."""

from __future__ import annotations

from typing import Any

from p6_mcp.domain.activity import Activity
from p6_mcp.domain.project import Project
from p6_mcp.domain.schedule import Schedule
from p6_mcp.exceptions import NotFoundError


def _baseline_pool(
    sch: Schedule,
    projects: list[Project],
    baseline_project_id: int | None,
    baseline_schedule: Schedule | None,
) -> tuple[Schedule, list[Activity], str]:
    if baseline_schedule is not None:
        bl_sch = baseline_schedule
        acts = bl_sch.activities_of(bl_sch.active_projects or bl_sch.projects)
        return bl_sch, acts, "separate baseline file"
    if baseline_project_id is not None:
        acts = [a for a in sch.activities if a.proj_id == baseline_project_id]
        if not acts:
            raise NotFoundError(
                f"No activities in baseline project {baseline_project_id}",
                hint="Call get_baselines to list baseline projects in this file.",
            )
        return sch, acts, f"baseline project {baseline_project_id} in file"
    bl_ids = {
        p.sum_base_proj_id for p in projects if p.sum_base_proj_id is not None
    } | {
        bp.proj_id for bp in sch.baseline_projects
        if bp.orig_proj_id in {p.proj_id for p in projects}
    }
    acts = [a for a in sch.activities if a.proj_id in bl_ids]
    if not acts:
        raise NotFoundError(
            "No baseline project found in this file",
            hint="Pass baseline_file_path or baseline_project_id, or export the "
            "XER with its baseline included.",
        )
    return sch, acts, "linked baseline project in file"


def compare_to_baseline(
    sch: Schedule,
    projects: list[Project],
    baseline_project_id: int | None = None,
    baseline_schedule: Schedule | None = None,
    tolerance_days: float = 0.0,
) -> dict[str, Any]:
    """Per-activity variance, added/deleted, logic & assignment changes, summary."""
    bl_sch, bl_acts, source = _baseline_pool(
        sch, projects, baseline_project_id, baseline_schedule
    )
    cur = {a.code: a for a in sch.activities_of(projects)}
    bl = {a.code: a for a in bl_acts}
    added = sorted(set(cur) - set(bl))
    deleted = sorted(set(bl) - set(cur))
    common = sorted(set(cur) & set(bl))

    variances: list[dict[str, Any]] = []
    slipped = gained = 0
    for code in common:
        a, b = cur[code], bl[code]
        cal = sch.calendar_for(a)
        row: dict[str, Any] = {"task_code": code, "task_name": a.name}
        changed = False
        for label, cur_d, bl_d in (
            ("start", a.start, b.start or b.planned_start),
            ("finish", a.finish, b.finish or b.planned_finish),
        ):
            if cur_d and bl_d and cal:
                v = cal.work_hours_between(bl_d, cur_d) / cal.day_hours
                if abs(v) > tolerance_days:
                    row[f"{label}_variance_days"] = round(v, 1)
                    row[f"baseline_{label}"] = bl_d
                    row[f"current_{label}"] = cur_d
                    changed = True
        dv = a.original_duration_hours - b.original_duration_hours
        if abs(dv) > 0.01:
            row["duration_change_hours"] = round(dv, 1)
            changed = True
        if changed:
            fv = row.get("finish_variance_days", 0)
            if isinstance(fv, (int, float)) and fv > 0:
                slipped += 1
            elif isinstance(fv, (int, float)) and fv < 0:
                gained += 1
            variances.append(row)
    variances.sort(
        key=lambda d: -abs(float(d.get("finish_variance_days") or 0))
    )

    # Logic changes on common activities
    def rel_set(s: Schedule, pool: dict[str, Activity]) -> set[tuple[str, str, str, float]]:
        ids = {a.task_id: c for c, a in pool.items()}
        out = set()
        for r in s.relationships:
            pc, sc = ids.get(r.pred_task_id), ids.get(r.task_id)
            if pc and sc:
                out.add((pc, sc, r.short_type, r.lag_hours))
        return out

    cur_rels = rel_set(sch, cur)
    bl_rels = rel_set(bl_sch, bl)
    rel_added = sorted(cur_rels - bl_rels)
    rel_removed = sorted(bl_rels - cur_rels)

    def asg_map(s: Schedule, pool: dict[str, Activity]) -> dict[str, dict[str, float]]:
        out: dict[str, dict[str, float]] = {}
        for code, a in pool.items():
            for x in s.assignments_by_task.get(a.task_id, []):
                rname = (
                    s.resources_by_id[x.rsrc_id].name
                    if x.rsrc_id in s.resources_by_id
                    else str(x.rsrc_id)
                )
                key = f"{code}|{rname}"
                out[key] = {
                    "qty": x.budgeted_qty, "cost": x.budgeted_cost,
                }
        return out

    cur_asg, bl_asg = asg_map(sch, cur), asg_map(bl_sch, bl)
    asg_changes: list[dict[str, Any]] = []
    for key in sorted(set(cur_asg) | set(bl_asg)):
        c, b2 = cur_asg.get(key), bl_asg.get(key)
        code, rname = key.split("|", 1)
        if c is None:
            asg_changes.append({"task_code": code, "resource": rname, "change": "removed"})
        elif b2 is None:
            asg_changes.append({"task_code": code, "resource": rname, "change": "added"})
        elif abs(c["cost"] - b2["cost"]) > 0.01 or abs(c["qty"] - b2["qty"]) > 0.01:
            asg_changes.append(
                {
                    "task_code": code, "resource": rname, "change": "modified",
                    "qty_delta": round(c["qty"] - b2["qty"], 2),
                    "cost_delta": round(c["cost"] - b2["cost"], 2),
                }
            )

    ms_var = [
        v for v in variances
        if cur[str(v["task_code"])].is_milestone
    ]
    crit_cur = {c for c, a in cur.items()
                if not a.is_completed and (a.total_float_hours or 1) <= 0}
    crit_bl = {c for c, a in bl.items()
               if not a.is_completed and (a.total_float_hours or 1) <= 0}
    return {
        "baseline_source": source,
        "tolerance_days": tolerance_days,
        "summary": {
            "compared": len(common),
            "added_activities": len(added),
            "deleted_activities": len(deleted),
            "changed": len(variances),
            "slipped": slipped,
            "gained": gained,
            "relationships_added": len(rel_added),
            "relationships_removed": len(rel_removed),
            "assignment_changes": len(asg_changes),
        },
        "added": added,
        "deleted": deleted,
        "variances": variances,
        "milestone_variances": ms_var,
        "relationships_added": [
            {"predecessor": p, "successor": s2, "type": t, "lag_hours": lg}
            for p, s2, t, lg in rel_added
        ],
        "relationships_removed": [
            {"predecessor": p, "successor": s2, "type": t, "lag_hours": lg}
            for p, s2, t, lg in rel_removed
        ],
        "assignment_changes": asg_changes,
        "critical_path_changes": {
            "now_critical": sorted(crit_cur - crit_bl),
            "no_longer_critical": sorted(crit_bl - crit_cur),
        },
    }
