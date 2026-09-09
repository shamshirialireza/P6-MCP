"""Activity filtering with the full §5.4 predicate set."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from p6_mcp.domain.activity import Activity
from p6_mcp.domain.schedule import Schedule
from p6_mcp.exceptions import InvalidArgumentError

_STATUS_ALIASES = {
    "not started": "TK_NotStart",
    "tk_notstart": "TK_NotStart",
    "in progress": "TK_Active",
    "active": "TK_Active",
    "tk_active": "TK_Active",
    "completed": "TK_Complete",
    "complete": "TK_Complete",
    "tk_complete": "TK_Complete",
}


def normalize_status(status: str) -> str:
    s = _STATUS_ALIASES.get(status.strip().lower())
    if s is None:
        raise InvalidArgumentError(
            f"Unknown status {status!r}",
            hint="Use Not Started / In Progress / Completed (or TK_* codes).",
        )
    return s


@dataclass(slots=True)
class ActivityFilter:
    """All optional predicates; only supplied ones are applied (AND semantics)."""

    status: list[str] | None = None
    task_type: list[str] | None = None
    wbs_id: int | None = None
    wbs_path_prefix: str | None = None
    activity_code: dict[str, str] | None = None  # {code_type: value}
    udf: dict[str, Any] | None = None  # {udf_name: value}
    calendar_id: int | None = None
    resource_id: int | None = None
    resource_name: str | None = None
    role_id: int | None = None
    name_contains: str | None = None
    code_contains: str | None = None
    code_regex: str | None = None
    start_between: tuple[datetime | None, datetime | None] | None = None
    finish_between: tuple[datetime | None, datetime | None] | None = None
    float_min_days: float | None = None
    float_max_days: float | None = None
    remaining_duration_min_days: float | None = None
    remaining_duration_max_days: float | None = None
    has_constraint: bool | None = None
    constraint_type: str | None = None
    is_critical: bool | None = None
    on_longest_path: bool | None = None
    has_no_predecessors: bool | None = None
    has_no_successors: bool | None = None
    is_behind_schedule: bool | None = None
    has_actuals: bool | None = None
    milestones_only: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


def _code_match(sch: Schedule, a: Activity, wanted: dict[str, str]) -> bool:
    have = {
        (str(c.get("code_type") or "").lower()): c for c in sch.codes_by_task.get(a.task_id, [])
    }
    for ctype, cval in wanted.items():
        c = have.get(ctype.lower())
        if c is None:
            return False
        val = str(c.get("code_value") or "")
        short = str(c.get("short_name") or "")
        if cval.lower() not in (val.lower(), short.lower()):
            return False
    return True


def _udf_match(sch: Schedule, a: Activity, wanted: dict[str, Any]) -> bool:
    have = {str(u.get("name") or "").lower(): u.get("value") for u in sch.task_udfs(a.task_id)} | {
        str(u.get("label") or "").lower(): u.get("value") for u in sch.task_udfs(a.task_id)
    }
    for name, val in wanted.items():
        actual = have.get(name.lower())
        if actual is None:
            return False
        if isinstance(val, dict):  # {"min": x, "max": y} range
            try:
                num = float(actual)  # type: ignore[arg-type]
            except (TypeError, ValueError):
                return False
            if "min" in val and num < float(val["min"]):
                return False
            if "max" in val and num > float(val["max"]):
                return False
        elif str(actual).lower() != str(val).lower():
            return False
    return True


def filter_activities(
    sch: Schedule, activities: list[Activity], flt: ActivityFilter
) -> list[Activity]:
    """Apply every supplied predicate; order-preserving."""
    out = activities
    if flt.status:
        codes = {normalize_status(s) for s in flt.status}
        out = [a for a in out if a.status in codes]
    if flt.task_type:
        types = set(flt.task_type)
        out = [a for a in out if a.task_type in types]
    if flt.milestones_only:
        out = [a for a in out if a.is_milestone]
    if flt.wbs_id is not None:
        ids = sch.wbs_descendant_ids(flt.wbs_id)
        out = [a for a in out if a.wbs_id in ids]
    if flt.wbs_path_prefix:
        pref = flt.wbs_path_prefix.lower()
        out = [a for a in out if sch.wbs_path(a.wbs_id).lower().startswith(pref)]
    if flt.activity_code:
        out = [a for a in out if _code_match(sch, a, flt.activity_code)]
    if flt.udf:
        out = [a for a in out if _udf_match(sch, a, flt.udf)]
    if flt.calendar_id is not None:
        out = [a for a in out if a.clndr_id == flt.calendar_id]
    if flt.resource_id is not None or flt.resource_name is not None:
        rid = flt.resource_id
        if rid is None and flt.resource_name is not None:
            rid = sch.resolve_resource(flt.resource_name).rsrc_id
        tasks = {x.task_id for x in sch.assignments_by_rsrc.get(rid or -1, [])}
        out = [a for a in out if a.task_id in tasks]
    if flt.role_id is not None:
        tasks = {x.task_id for x in sch.assignments if x.role_id == flt.role_id}
        out = [a for a in out if a.task_id in tasks]
    if flt.name_contains:
        needle = flt.name_contains.lower()
        out = [a for a in out if needle in a.name.lower()]
    if flt.code_contains:
        needle = flt.code_contains.lower()
        out = [a for a in out if needle in a.code.lower()]
    if flt.code_regex:
        try:
            rx = re.compile(flt.code_regex)
        except re.error as exc:
            raise InvalidArgumentError(f"Invalid code_regex: {exc}") from exc
        out = [a for a in out if rx.search(a.code)]
    if flt.start_between:
        lo, hi = flt.start_between
        out = [
            a
            for a in out
            if a.start is not None
            and (lo is None or a.start >= lo)
            and (hi is None or a.start <= hi)
        ]
    if flt.finish_between:
        lo, hi = flt.finish_between
        out = [
            a
            for a in out
            if a.finish is not None
            and (lo is None or a.finish >= lo)
            and (hi is None or a.finish <= hi)
        ]
    if flt.float_min_days is not None or flt.float_max_days is not None:

        def tf_ok(a: Activity) -> bool:
            days = sch.hours_to_days(a, a.total_float_hours)
            if days is None:
                return False
            if flt.float_min_days is not None and days < flt.float_min_days:
                return False
            return not (flt.float_max_days is not None and days > flt.float_max_days)

        out = [a for a in out if tf_ok(a)]
    if flt.remaining_duration_min_days is not None or flt.remaining_duration_max_days is not None:

        def rd_ok(a: Activity) -> bool:
            days = sch.hours_to_days(a, a.remaining_duration_hours) or 0.0
            if (
                flt.remaining_duration_min_days is not None
                and days < flt.remaining_duration_min_days
            ):
                return False
            return not (
                flt.remaining_duration_max_days is not None
                and days > flt.remaining_duration_max_days
            )

        out = [a for a in out if rd_ok(a)]
    if flt.has_constraint is not None:
        out = [a for a in out if a.has_constraint == flt.has_constraint]
    if flt.constraint_type:
        out = [a for a in out if flt.constraint_type in (a.cstr_type, a.f("cstr_type2"))]
    if flt.is_critical is not None:

        def crit(a: Activity) -> bool:
            return (
                not a.is_completed and a.total_float_hours is not None and a.total_float_hours <= 0
            )

        out = [a for a in out if crit(a) == flt.is_critical]
    if flt.on_longest_path is not None:
        out = [a for a in out if a.driving_path_flag == flt.on_longest_path]
    if flt.has_no_predecessors is not None:
        out = [a for a in out if (a.task_id not in sch.predecessors_of) == flt.has_no_predecessors]
    if flt.has_no_successors is not None:
        out = [a for a in out if (a.task_id not in sch.successors_of) == flt.has_no_successors]
    if flt.is_behind_schedule is not None:

        def behind(a: Activity) -> bool:
            if a.planned_finish is None or a.finish is None:
                return False
            return a.finish > a.planned_finish

        out = [a for a in out if behind(a) == flt.is_behind_schedule]
    if flt.has_actuals is not None:
        out = [
            a
            for a in out
            if (a.act_start is not None or a.act_finish is not None) == flt.has_actuals
        ]
    return out
