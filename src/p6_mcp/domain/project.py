"""Project (PROJECT row) and WBS (PROJWBS row) entities."""

from __future__ import annotations

from datetime import datetime

from p6_mcp.domain.base import CRITICAL_PATH_TYPE, WBS_STATUS, Entity, label_of


class Project(Entity):
    """One PROJECT row. ``project_flag='N'`` rows are baselines."""

    __slots__ = ()

    @property
    def proj_id(self) -> int:
        return int(self.num("proj_id"))

    @property
    def short_name(self) -> str:
        return self.raw("proj_short_name")

    @property
    def is_baseline(self) -> bool:
        return self.f("project_flag") is False

    @property
    def orig_proj_id(self) -> int | None:
        v = self.f("orig_proj_id")
        return int(v) if v is not None else None

    @property
    def sum_base_proj_id(self) -> int | None:
        v = self.f("sum_base_proj_id")
        return int(v) if v is not None else None

    @property
    def clndr_id(self) -> int | None:
        v = self.f("clndr_id")
        return int(v) if v is not None else None

    @property
    def data_date(self) -> datetime | None:
        """P6's current data date is last_recalc_date."""
        return self.date("last_recalc_date")

    @property
    def plan_start(self) -> datetime | None:
        return self.date("plan_start_date")

    @property
    def plan_end(self) -> datetime | None:
        return self.date("plan_end_date")

    @property
    def scd_end(self) -> datetime | None:
        """Scheduled (must-finish-by driven) end date."""
        return self.date("scd_end_date")

    @property
    def critical_path_type(self) -> str | None:
        return self.f("critical_path_type")

    @property
    def critical_path_type_label(self) -> str | None:
        return label_of(CRITICAL_PATH_TYPE, self.critical_path_type)

    @property
    def critical_drtn_hr_cnt(self) -> float:
        return self.num("critical_drtn_hr_cnt")


class Wbs(Entity):
    """One PROJWBS row (WBS node; the project node has proj_node_flag=Y)."""

    __slots__ = ()

    @property
    def wbs_id(self) -> int:
        return int(self.num("wbs_id"))

    @property
    def proj_id(self) -> int:
        return int(self.num("proj_id"))

    @property
    def parent_wbs_id(self) -> int | None:
        v = self.f("parent_wbs_id")
        return int(v) if v is not None else None

    @property
    def short_name(self) -> str:
        return self.raw("wbs_short_name")

    @property
    def name(self) -> str:
        return self.raw("wbs_name")

    @property
    def is_project_node(self) -> bool:
        return bool(self.f("proj_node_flag"))

    @property
    def status_label(self) -> str | None:
        return label_of(WBS_STATUS, self.f("status_code"))
