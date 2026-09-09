"""XER-vs-XER update comparison and multi-update trend."""

from __future__ import annotations

from typing import Any

from p6_mcp.domain.activity import Activity
from p6_mcp.domain.project import Project
from p6_mcp.domain.schedule import Schedule
from p6_mcp.exceptions import InvalidArgumentError
from p6_mcp.services.analysis.cost import activity_costs
from p6_mcp.services.analysis.earned_value import earned_value
from p6_mcp.services.analysis.progress import progress_summary

_TRACKED_FIELDS = (
    ("task_name", "renamed"),
    ("status_code", "status_changed"),
    ("target_drtn_hr_cnt", "duration_changed"),
    ("remain_drtn_hr_cnt", "remaining_changed"),
    ("total_float_hr_cnt", "float_changed"),
    ("cstr_type", "constraint_changed"),
    ("cstr_date", "constraint_changed"),
    ("clndr_id", "calendar_changed"),
    ("wbs_id", "wbs_moved"),
)
_DATE_FIELDS = (
    "act_start_date",
    "act_end_date",
    "early_start_date",
    "early_end_date",
    "late_start_date",
    "late_end_date",
    "target_start_date",
    "target_end_date",
)


def _match_projects(
    cur: Schedule, prev: Schedule, project_match: str
) -> list[tuple[Project, Project]]:
    if project_match not in ("short_name", "id", "guid"):
        raise InvalidArgumentError(
            f"Unknown project_match {project_match!r}",
            hint="Use short_name, id, or guid.",
        )

    def key(p: Project) -> Any:
        if project_match == "short_name":
            return p.short_name.lower()
        if project_match == "id":
            return p.proj_id
        return p.raw("guid") or p.short_name.lower()

    prev_map = {key(p): p for p in prev.active_projects or prev.projects}
    pairs = []
    for p in cur.active_projects or cur.projects:
        q = prev_map.get(key(p))
        if q is not None:
            pairs.append((p, q))
    return pairs


def diff_schedules(
    cur: Schedule, prev: Schedule, project_match: str = "short_name"
) -> dict[str, Any]:
    """Full update-to-update diff, grouped summary + per-activity detail."""
    pairs = _match_projects(cur, prev, project_match)
    cur_acts = {a.code: a for p, _ in pairs for a in cur.activities if a.proj_id == p.proj_id}
    prev_acts = {a.code: a for _, q in pairs for a in prev.activities if a.proj_id == q.proj_id}
    added = sorted(set(cur_acts) - set(prev_acts))
    deleted = sorted(set(prev_acts) - set(cur_acts))
    changes: list[dict[str, Any]] = []
    progressed: list[str] = []
    for code in sorted(set(cur_acts) & set(prev_acts)):
        a, b = cur_acts[code], prev_acts[code]
        entry: dict[str, Any] = {"task_code": code, "task_name": a.name, "changes": {}}
        for field_name, label in _TRACKED_FIELDS:
            va, vb = a.f(field_name), b.f(field_name)
            if va != vb:
                entry["changes"].setdefault(label, {})[field_name] = {
                    "from": vb,
                    "to": va,
                }
        for field_name in _DATE_FIELDS:
            va, vb = a.date(field_name), b.date(field_name)
            if va != vb:
                entry["changes"].setdefault("dates", {})[field_name] = {
                    "from": vb,
                    "to": va,
                }
        ca, cb = activity_costs(cur, a), activity_costs(prev, b)
        for k in ("budgeted", "actual", "remaining"):
            if abs(ca[k] - cb[k]) > 0.01:
                entry["changes"].setdefault("cost", {})[k] = {
                    "from": round(cb[k], 2),
                    "to": round(ca[k], 2),
                }
        if a.percent_complete() > b.percent_complete() + 0.01:
            progressed.append(code)
        if entry["changes"]:
            changes.append(entry)

    def rel_set(s: Schedule, pool: dict[str, Activity]) -> set[tuple[str, str, str, float]]:
        ids = {a.task_id: c for c, a in pool.items()}
        return {
            (ids[r.pred_task_id], ids[r.task_id], r.short_type, r.lag_hours)
            for r in s.relationships
            if r.pred_task_id in ids and r.task_id in ids
        }

    cur_rels, prev_rels = rel_set(cur, cur_acts), rel_set(prev, prev_acts)

    def cal_fingerprint(s: Schedule) -> dict[str, Any]:
        return {
            c.name: {
                "week_hours": c.week_hours,
                "exceptions": len(c.parsed.exceptions),
            }
            for c in s.calendars
        }

    cal_cur, cal_prev = cal_fingerprint(cur), cal_fingerprint(prev)
    cal_changes = sorted(
        name for name in set(cal_cur) | set(cal_prev) if cal_cur.get(name) != cal_prev.get(name)
    )
    cur_finish = max(
        (a.finish for a in cur_acts.values() if a.finish and not a.is_loe),
        default=None,
    )
    prev_finish = max(
        (a.finish for a in prev_acts.values() if a.finish and not a.is_loe),
        default=None,
    )
    return {
        "project_match": project_match,
        "matched_projects": [{"current": p.short_name, "previous": q.short_name} for p, q in pairs],
        "summary": {
            "activities_added": len(added),
            "activities_deleted": len(deleted),
            "activities_changed": len(changes),
            "activities_progressed": len(progressed),
            "relationships_added": len(cur_rels - prev_rels),
            "relationships_removed": len(prev_rels - cur_rels),
            "calendars_changed": cal_changes,
            "previous_finish": prev_finish,
            "current_finish": cur_finish,
            "data_date_previous": prev.data_date(),
            "data_date_current": cur.data_date(),
        },
        "added": added,
        "deleted": deleted,
        "progressed": progressed,
        "changes": changes,
        "relationships_added": [
            {"predecessor": p, "successor": s, "type": t, "lag_hours": lg}
            for p, s, t, lg in sorted(cur_rels - prev_rels)
        ],
        "relationships_removed": [
            {"predecessor": p, "successor": s, "type": t, "lag_hours": lg}
            for p, s, t, lg in sorted(prev_rels - cur_rels)
        ],
    }


def schedule_trend(schedules: list[tuple[str, Schedule]]) -> dict[str, Any]:
    """Key metrics across a series of updates (ordered as given)."""
    rows: list[dict[str, Any]] = []
    for label, s in schedules:
        projects = s.active_projects or s.projects
        prog = progress_summary(s, projects)
        ev = earned_value(s, projects, time_phased=False)
        crit = sum(
            1
            for a in s.activities_of(projects)
            if not a.is_completed and a.total_float_hours is not None and a.total_float_hours <= 0
        )
        rows.append(
            {
                "file": label,
                "data_date": prog["data_date"],
                "forecast_finish": prog["forecast_finish"],
                "percent_complete_duration": prog["percent_complete"]["by_duration"],
                "critical_count": crit,
                "cpi": ev["metrics"]["CPI"],
                "spi": ev["metrics"]["SPI"],
            }
        )
    return {"updates": rows}
