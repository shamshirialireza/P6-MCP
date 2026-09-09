"""Composite schedule health score and the quick quality check."""

from __future__ import annotations

from typing import Any

from p6_mcp.domain.activity import Activity
from p6_mcp.domain.project import Project
from p6_mcp.domain.schedule import Schedule
from p6_mcp.services.analysis import logic_health
from p6_mcp.services.analysis.progress import invalid_dates, status_update_check
from p6_mcp.services.analysis.thresholds import (
    HEALTH_WEIGHTS_DEFAULT,
    HIGH_FLOAT_DAYS_DEFAULT,
    LONG_DURATION_DAYS_DEFAULT,
)


def check_schedule_quality(
    sch: Schedule,
    projects: list[Project],
    long_duration_days: float = LONG_DURATION_DAYS_DEFAULT,
    high_float_days: float = HIGH_FLOAT_DAYS_DEFAULT,
) -> dict[str, Any]:
    """Quick quality sweep: every common defect with offending activity codes."""
    acts = sch.activities_of(projects)
    incomplete = [a for a in acts if not a.is_completed]
    lh = logic_health.analyze_logic_health(sch, projects)
    upd = status_update_check(sch, projects)

    def codes(xs: list[Activity]) -> list[str]:
        return sorted(a.code for a in xs)

    long_dur = [
        a
        for a in incomplete
        if not a.is_milestone
        and not a.is_loe
        and (d := sch.hours_to_days(a, a.remaining_duration_hours)) is not None
        and d > long_duration_days
    ]
    high_float = [
        a
        for a in incomplete
        if (d := sch.hours_to_days(a, a.total_float_hours)) is not None and d > high_float_days
    ]
    neg_float = [
        a for a in incomplete if a.total_float_hours is not None and a.total_float_hours < 0
    ]
    no_rsrc = [
        a
        for a in incomplete
        if not a.is_milestone
        and not a.is_loe
        and a.original_duration_hours > 0
        and not sch.assignments_by_task.get(a.task_id)
        and not sch.expenses_by_task.get(a.task_id)
    ]
    missing_dates = [a for a in acts if a.start is None or a.finish is None]
    loe_unlinked = [
        a
        for a in acts
        if a.is_loe and (a.task_id not in sch.predecessors_of or a.task_id not in sch.successors_of)
    ]
    mile_with_dur = [a for a in acts if a.is_milestone and a.original_duration_hours > 0]
    zero_remaining_active = [
        a
        for a in incomplete
        if a.is_in_progress and not a.is_milestone and a.remaining_duration_hours == 0
    ]
    hard_constrained = [a for a in incomplete if a.has_hard_constraint]

    return {
        "activity_count": len(acts),
        "checks": {
            "no_predecessors": codes(lh["open_ends"]["no_predecessors"]),
            "no_successors": codes(lh["open_ends"]["no_successors"]),
            "long_duration": codes(long_dur),
            "high_float": codes(high_float),
            "negative_float": codes(neg_float),
            "no_resources": codes(no_rsrc),
            "missing_dates": codes(missing_dates),
            "hard_constraints": codes(hard_constrained),
            "invalid_dates": [d["task_code"] for d in invalid_dates(sch, projects)],
            "out_of_sequence": [d["successor"] for d in lh["out_of_sequence"]],
            "loe_without_logic": codes(loe_unlinked),
            "milestones_with_duration": codes(mile_with_dur),
            "in_progress_zero_remaining": codes(zero_remaining_active),
            "finish_dangles_ss_only": codes(lh["dangling"]["finish_dangles"]),
            "start_dangles_ff_only": codes(lh["dangling"]["start_dangles"]),
            "redundant_relationships": lh["redundant"],
            "circular_logic": lh["circular"],
            "leads": lh["relationship_mix"]["leads"],
            "lags": lh["relationship_mix"]["lags"],
            "status_update": upd,
        },
        "relationship_mix": lh["relationship_mix"],
        "thresholds": {
            "long_duration_days": long_duration_days,
            "high_float_days": high_float_days,
        },
    }


def health_score(
    sch: Schedule,
    projects: list[Project],
    weights: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Weighted 0-100 score with per-component breakdown and recommendations."""
    w = dict(HEALTH_WEIGHTS_DEFAULT)
    if weights:
        w.update(weights)
    total_w = sum(w.values()) or 1.0
    q = check_schedule_quality(sch, projects)
    acts = sch.activities_of(projects)
    incomplete = [a for a in acts if not a.is_completed]
    n = max(len(incomplete), 1)
    rels = q["relationship_mix"]["total_relationships"] or 1
    checks = q["checks"]

    def ratio_score(bad: int, pool: int, tolerance_pct: float = 5.0) -> float:
        """100 when clean, linear to 0 at 4× the tolerance."""
        pct = bad / max(pool, 1) * 100
        return max(0.0, 100.0 * (1 - pct / (4 * tolerance_pct)))

    components: dict[str, dict[str, Any]] = {}
    components["logic"] = {
        "score": ratio_score(len(checks["no_predecessors"]) + len(checks["no_successors"]), n * 2),
        "detail": f"{len(checks['no_predecessors'])} missing preds, "
        f"{len(checks['no_successors'])} missing succs",
    }
    components["leads_lags"] = {
        "score": ratio_score(checks["leads"] * 3 + checks["lags"], rels, 10.0),
        "detail": f"{checks['leads']} leads, {checks['lags']} lags of {rels} relationships",
    }
    components["constraints"] = {
        "score": ratio_score(len(checks["hard_constraints"]), n),
        "detail": f"{len(checks['hard_constraints'])} hard constraints",
    }
    neg = len(checks["negative_float"])
    components["float"] = {
        "score": max(0.0, ratio_score(len(checks["high_float"]), n, 10.0) - neg * 15),
        "detail": f"{len(checks['high_float'])} high float, {neg} negative float",
    }
    components["duration"] = {
        "score": ratio_score(len(checks["long_duration"]), n, 10.0),
        "detail": f"{len(checks['long_duration'])} long-duration activities",
    }
    components["invalid_dates"] = {
        "score": 100.0
        if not checks["invalid_dates"]
        else max(0.0, 100 - 20 * len(checks["invalid_dates"])),
        "detail": f"{len(checks['invalid_dates'])} activities with invalid dates",
    }
    components["resources"] = {
        "score": ratio_score(len(checks["no_resources"]), n, 15.0),
        "detail": f"{len(checks['no_resources'])} unresourced activities",
    }
    oos = len(checks["out_of_sequence"])
    components["progress"] = {
        "score": max(
            0.0,
            100.0 - 15 * oos - 10 * len(checks["status_update"]["remaining_duration_anomalies"]),
        ),
        "detail": f"{oos} out-of-sequence, "
        f"{len(checks['status_update']['remaining_duration_anomalies'])} status anomalies",
    }
    fs_pct = q["relationship_mix"]["percentages"].get("FS", 100.0)
    components["relationship_types"] = {
        "score": max(0.0, min(100.0, (fs_pct - 50) * 2)),
        "detail": f"{fs_pct}% FS relationships",
    }

    score = sum(components[k]["score"] * w.get(k, 0.0) for k in components) / total_w
    recommendations = [
        rec
        for key, rec in [
            ("logic", "Add missing predecessors/successors to close open ends."),
            ("leads_lags", "Replace leads with activity splits; justify or remove lags."),
            ("constraints", "Replace hard constraints with logic where possible."),
            ("float", "Investigate negative float and unrealistically high float."),
            ("duration", "Break long activities into measurable pieces."),
            ("invalid_dates", "Correct actuals after / forecasts before the data date."),
            ("resources", "Load resources or costs on all remaining work."),
            ("progress", "Repair out-of-sequence progress and status anomalies."),
            ("relationship_types", "Prefer Finish-to-Start relationships."),
        ]
        if components[key]["score"] < 70
    ]
    return {
        "score": round(score, 1),
        "grade": (
            "A"
            if score >= 90
            else "B"
            if score >= 80
            else "C"
            if score >= 65
            else "D"
            if score >= 50
            else "F"
        ),
        "components": {
            k: {"score": round(v["score"], 1), "weight": w.get(k, 0.0), "detail": v["detail"]}
            for k, v in components.items()
        },
        "recommendations": recommendations,
    }
