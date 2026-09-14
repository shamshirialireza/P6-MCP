"""Activity (TASK row) entity."""

from __future__ import annotations

from datetime import datetime

from p6_mcp.domain.base import (
    CSTR_TYPE,
    HARD_CONSTRAINTS,
    STATUS_CODE,
    TASK_TYPE,
    Entity,
    label_of,
)

MILESTONE_TYPES = frozenset({"TT_Mile", "TT_FinMile"})
#: Task types DCMA exempts from most logic/duration checks.
SUMMARY_LIKE_TYPES = frozenset({"TT_LOE", "TT_WBS"})


class Activity(Entity):
    """One TASK row with typed accessors and schedule-semantics helpers."""

    __slots__ = ()

    @property
    def task_id(self) -> int:
        return int(self.num("task_id"))

    @property
    def proj_id(self) -> int:
        return int(self.num("proj_id"))

    @property
    def wbs_id(self) -> int | None:
        v = self.f("wbs_id")
        return int(v) if v is not None else None

    @property
    def clndr_id(self) -> int | None:
        v = self.f("clndr_id")
        return int(v) if v is not None else None

    @property
    def code(self) -> str:
        return self.raw("task_code")

    @property
    def name(self) -> str:
        return self.raw("task_name")

    @property
    def status(self) -> str:
        return self.raw("status_code")

    @property
    def status_label(self) -> str | None:
        return label_of(STATUS_CODE, self.status or None)

    @property
    def task_type(self) -> str:
        return self.raw("task_type")

    @property
    def type_label(self) -> str | None:
        return label_of(TASK_TYPE, self.task_type or None)

    # -- classification ----------------------------------------------------

    @property
    def is_milestone(self) -> bool:
        return self.task_type in MILESTONE_TYPES

    @property
    def is_loe(self) -> bool:
        return self.task_type == "TT_LOE"

    @property
    def is_wbs_summary(self) -> bool:
        return self.task_type == "TT_WBS"

    @property
    def is_completed(self) -> bool:
        return self.status == "TK_Complete"

    @property
    def is_in_progress(self) -> bool:
        return self.status == "TK_Active"

    @property
    def is_not_started(self) -> bool:
        return self.status == "TK_NotStart"

    # -- durations & float (hours; day conversion is calendar-aware upstream) --

    @property
    def original_duration_hours(self) -> float:
        return self.num("target_drtn_hr_cnt")

    @property
    def remaining_duration_hours(self) -> float:
        return self.num("remain_drtn_hr_cnt")

    @property
    def total_float_hours(self) -> float | None:
        v = self.f("total_float_hr_cnt")
        return float(v) if v is not None else None

    @property
    def free_float_hours(self) -> float | None:
        v = self.f("free_float_hr_cnt")
        return float(v) if v is not None else None

    @property
    def driving_path_flag(self) -> bool:
        return bool(self.f("driving_path_flag"))

    # -- dates -------------------------------------------------------------

    @property
    def act_start(self) -> datetime | None:
        return self.date("act_start_date")

    @property
    def act_finish(self) -> datetime | None:
        return self.date("act_end_date")

    @property
    def early_start(self) -> datetime | None:
        return self.date("early_start_date")

    @property
    def early_finish(self) -> datetime | None:
        return self.date("early_end_date")

    @property
    def late_start(self) -> datetime | None:
        return self.date("late_start_date")

    @property
    def late_finish(self) -> datetime | None:
        return self.date("late_end_date")

    @property
    def planned_start(self) -> datetime | None:
        return self.date("target_start_date")

    @property
    def planned_finish(self) -> datetime | None:
        return self.date("target_end_date")

    @property
    def start(self) -> datetime | None:
        """Current start: actual if started, else early/planned."""
        return self.act_start or self.early_start or self.planned_start

    @property
    def finish(self) -> datetime | None:
        """Current finish: actual if complete, else early/planned."""
        if self.is_completed:
            return self.act_finish or self.early_finish or self.planned_finish
        return self.early_finish or self.planned_finish or self.act_finish

    # -- constraints -------------------------------------------------------

    @property
    def cstr_type(self) -> str | None:
        return self.f("cstr_type")  # type: ignore[no-any-return]

    @property
    def cstr_label(self) -> str | None:
        return label_of(CSTR_TYPE, self.cstr_type)

    @property
    def cstr_date(self) -> datetime | None:
        return self.date("cstr_date")

    @property
    def has_constraint(self) -> bool:
        return bool(self.cstr_type) or bool(self.f("cstr_type2"))

    @property
    def has_hard_constraint(self) -> bool:
        return self.cstr_type in HARD_CONSTRAINTS or self.f("cstr_type2") in HARD_CONSTRAINTS

    # -- progress ----------------------------------------------------------

    @property
    def physical_pct(self) -> float:
        return self.num("phys_complete_pct")

    def percent_complete(self) -> float:
        """Percent complete per the activity's ``complete_pct_type`` (0-100)."""
        cpt = self.raw("complete_pct_type")
        if self.is_completed:
            return 100.0
        if self.is_not_started:
            return 0.0
        if cpt == "CP_Phys":
            return self.physical_pct
        if cpt == "CP_Units":
            act = self.num("act_work_qty") + self.num("act_equip_qty")
            rem = self.num("remain_work_qty") + self.num("remain_equip_qty")
            total = act + rem
            return (act / total * 100.0) if total else 0.0
        od, rd = self.original_duration_hours, self.remaining_duration_hours
        if od <= 0:
            return 0.0
        return max(0.0, min(100.0, (od - rd) / od * 100.0))
