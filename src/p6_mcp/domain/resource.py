"""Resource (RSRC) and assignment (TASKRSRC) entities."""

from __future__ import annotations

from datetime import datetime

from p6_mcp.domain.base import RSRC_TYPE, Entity, label_of


class Resource(Entity):
    """One RSRC row."""

    __slots__ = ()

    @property
    def rsrc_id(self) -> int:
        return int(self.num("rsrc_id"))

    @property
    def parent_rsrc_id(self) -> int | None:
        v = self.f("parent_rsrc_id")
        return int(v) if v is not None else None

    @property
    def name(self) -> str:
        return self.raw("rsrc_name")

    @property
    def short_name(self) -> str:
        return self.raw("rsrc_short_name")

    @property
    def rsrc_type(self) -> str:
        return self.raw("rsrc_type")

    @property
    def type_label(self) -> str | None:
        return label_of(RSRC_TYPE, self.rsrc_type or None)

    @property
    def clndr_id(self) -> int | None:
        v = self.f("clndr_id")
        return int(v) if v is not None else None

    @property
    def is_active(self) -> bool:
        return self.f("active_flag") is not False


class Assignment(Entity):
    """One TASKRSRC row: a resource/role assignment on an activity."""

    __slots__ = ()

    @property
    def taskrsrc_id(self) -> int:
        return int(self.num("taskrsrc_id"))

    @property
    def task_id(self) -> int:
        return int(self.num("task_id"))

    @property
    def proj_id(self) -> int | None:
        v = self.f("proj_id")
        return int(v) if v is not None else None

    @property
    def rsrc_id(self) -> int | None:
        v = self.f("rsrc_id")
        return int(v) if v is not None else None

    @property
    def role_id(self) -> int | None:
        v = self.f("role_id")
        return int(v) if v is not None else None

    @property
    def rsrc_type(self) -> str:
        return self.raw("rsrc_type")

    # Quantities (hours for labor/nonlabor; units for material)
    @property
    def budgeted_qty(self) -> float:
        return self.num("target_qty")

    @property
    def actual_qty(self) -> float:
        return self.num("act_reg_qty") + self.num("act_ot_qty")

    @property
    def remaining_qty(self) -> float:
        return self.num("remain_qty")

    @property
    def at_completion_qty(self) -> float:
        return self.actual_qty + self.remaining_qty

    # Costs
    @property
    def budgeted_cost(self) -> float:
        return self.num("target_cost")

    @property
    def actual_cost(self) -> float:
        return self.num("act_reg_cost") + self.num("act_ot_cost")

    @property
    def remaining_cost(self) -> float:
        return self.num("remain_cost")

    @property
    def at_completion_cost(self) -> float:
        return self.actual_cost + self.remaining_cost

    # Dates
    @property
    def start(self) -> datetime | None:
        return (
            self.date("act_start_date")
            or self.date("restart_date")
            or self.date("target_start_date")
        )

    @property
    def finish(self) -> datetime | None:
        return self.date("act_end_date") or self.date("reend_date") or self.date("target_end_date")

    @property
    def planned_start(self) -> datetime | None:
        return self.date("target_start_date")

    @property
    def planned_finish(self) -> datetime | None:
        return self.date("target_end_date")

    @property
    def curve_id(self) -> int | None:
        v = self.f("curv_id")
        return int(v) if v is not None else None
