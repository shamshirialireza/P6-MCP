"""WBS (PROJWBS row) entity."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity, label_of

if TYPE_CHECKING:
    pass

# Enums from base.py would be imported here if needed
# For now, we'll reference them as strings and let base.label_of handle translation


class Wbs(Entity):
    """One PROJWBS row with typed accessors and schedule-semantics helpers."""

    __slots__ = ()

    @property
    def wbs_id(self) -> int:
        return int(self.num("wbs_id"))

    @property
    def proj_id(self) -> int:
        return int(self.num("proj_id"))

    @property
    def wbs_short_name(self) -> str:
        return self.raw("wbs_short_name")

    @property
    def status(self) -> str:
        return self.raw("status_code")

    @property
    def status_label(self) -> str | None:
        # Assuming WS_* status codes - would need to check actual P6 codes
        return label_of(
            {
                "WS_Open": "Active",
                "WS_Closed": "Inactive",
                "WS_Planned": "Planned",
                "WS_NotStarted": "What-If",
            },
            self.status,
        )

    @property
    def anticip_start_date(self) -> datetime | None:
        return self.date("anticip_start_date")

    @property
    def anticip_end_date(self) -> datetime | None:
        return self.date("anticip_end_date")

    @property
    def obs_id(self) -> int | None:
        v = self.f("obs_id")
        return int(v) if v is not None else None

    @property
    def phase_id(self) -> int | None:
        v = self.f("phase_id")
        return int(v) if v is not None else None

    @property
    def proj_node_flag(self) -> bool:
        return bool(self.f("proj_node_flag"))

    @property
    def sum_data_flag(self) -> bool:
        return bool(self.f("sum_data_flag"))

    @property
    def est_wt(self) -> float:
        return self.num("est_wt")

    @property
    def orig_cost(self) -> float:
        return self.num("orig_cost")

    @property
    def indep_remain_total_cost(self) -> float:
        return self.num("indep_remain_total_cost")

    @property
    def indep_remain_work_qty(self) -> float:
        return self.num("indep_remain_work_qty")

    @property
    def ev_compute_type(self) -> str:
        return self.raw("ev_compute_type")

    @property
    def ev_etc_compute_type(self) -> str:
        return self.raw("ev_etc_compute_type")

    @property
    def ev_etc_user_value(self) -> float:
        return self.num("ev_etc_user_value")

    @property
    def ev_user_pct(self) -> float:
        return self.num("ev_user_pct")

    @property
    def ann_dscnt_rate_pct(self) -> float:
        return self.num("ann_dscnt_rate_pct")

    @property
    def dscnt_period_type(self) -> str:
        return self.raw("dscnt_period_type")

    @property
    def plan_open_state(self) -> str:
        return self.raw("plan_open_state")

    @property
    def seq_num(self) -> int:
        return int(self.num("seq_num"))

    @property
    def guid(self) -> str:
        return self.raw("guid")
