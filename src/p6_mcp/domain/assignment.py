"""Assignment (TASKRSRC row) entity."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity, label_of

if TYPE_CHECKING:
    from p6_mcp.parser.reader import Table

class Assignment(Entity):
    """One TASKRSRC row with typed accessors."""

    __slots__ = ()

    @property
    def task_id(self) -> int:
        return int(self.num("task_id"))

    @property
    def rsrc_id(self) -> int:
        return int(self.num("rsrc_id"))

    @property
    def role_id(self) -> int | None:
        v = self.f("role_id")
        return int(v) if v is not None else None

    @property
    def acct_id(self) -> int | None:
        v = self.f("acct_id")
        return int(v) if v is not None else None

    @property
    def rsrc_type(self) -> str:
        return self.raw("rsrc_type")

    @property
    def remain_qty(self) -> float:
        return self.num("remain_qty")

    @property
    def remain_cost(self) -> float:
        return self.num("remain_cost")

    @property
    def cost_per_qty(self) -> float:
        return self.num("cost_per_qty")

    @property
    def cost_per_qty_source(self) -> str:
        return self.raw("cost_per_qty_source_type")

    @property
    def rate_type(self) -> str:
        return self.raw("rate_type")

    @property
    def target_start_date(self) -> datetime | None:
        return self.date("target_start_date")

    @property
    def target_end_date(self) -> datetime | None:
        return self.date("target_end_date")

    @property
    def act_start_date(self) -> datetime | None:
        return self.date("act_start_date")

    @property
    def act_end_date(self) -> datetime | None:
        return self.date("act_end_date")

    @property
    def restart_date(self) -> datetime | None:
        return self.date("restart_date")

    @property
    def reend_date(self) -> datetime | None:
        return self.date("reend_date")

    @property
    def target_lag_hr_cnt(self) -> float:
        return self.num("target_lag_drtn_hr_cnt")

    @property
    def relag_drtn_hr_cnt(self) -> float:
        return self.num("relag_drtn_hr_cnt")

    @property
    def target_qty_per_hr(self) -> float:
        return self.num("target_qty_per_hr")

    @property
    def remain_qty_per_hr(self) -> float:
        return self.num("remain_qty_per_hr")

    @property
    def target_crv(self) -> str:
        return self.raw("target_crv")

    @property
    def remain_crv(self) -> str:
        return self.raw("remain_crv")

    @property
    def actual_crv(self) -> str:
        return self.raw("actual_crv")

    @property
    def curv_id(self) -> int | None:
        v = self.f("curv_id")
        return int(v) if v is not None else None

    @property
    def act_this_per_qty(self) -> float:
        return self.num("act_this_per_qty")

    @property
    def act_this_per_cost(self) -> float:
        return self.num("act_this_per_cost")

    @property
    def act_ot_qty(self) -> float:
        return self.num("act_ot_qty")

    @property
    def act_ot_cost(self) -> float:
        return self.num("act_ot_cost")

    @property
    def act_reg_qty(self) -> float:
        return self.num("act_reg_qty")

    @property
    def act_reg_cost(self) -> float:
        return self.num("act_reg_cost")

    @property
    def ot_factor(self) -> float:
        return self.num("ot_factor")

    @property
    def skill_level(self) -> int:
        return int(self.num("skill_level"))

    @property
    def cost_qty_link_flag(self) -> bool:
        return bool(self.f("cost_qty_link_flag"))

    @property
    def rollup_dates_flag(self) -> bool:
        return bool(self.f("rollup_dates_flag"))

    @property
    def ts_pend_act_end_flag(self) -> bool:
        return bool(self.f("ts_pend_act_end_flag"))

    @property
    def pobs_id(self) -> int | None:
        v = self.f("pobs_id")
        return int(v) if v is not None else None

    @property
    def cbs_id(self) -> int | None:
        v = self.f("cbs_id")
        return int(v) if v is not None else None

    @property
    def has_rsrchours(self) -> bool:
        return bool(self.f("has_rsrchours"))

    @property
    def taskrsrc_sum_id(self) -> int | None:
        v = self.f("taskrsrc_sum_id")
        return int(v) if v is not None else None

    @property
    def guid(self) -> str:
        return self.raw("guid")

    @property
    def create_date(self) -> datetime | None:
        return self.date("create_date")

    @property
    def create_user(self) -> str:
        return self.raw("create_user")