"""Schedule options (SCHEDOPTIONS)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity

if TYPE_CHECKING:
    from p6_mcp.parser.reader import Table

class ScheduleOptions(Entity):
    """One SCHEDOPTIONS row - schedule calculation options."""

    __slots__ = ()

    @property
    def options_id(self) -> int:
        return int(self.num("options_id"))

    @property
    def proj_id(self) -> int:
        return int(self.num("proj_id"))

    @property
    def retain_logic(self) -> bool:
        return bool(self.f("retain_logic"))

    @property
    def critical_path_type(self) -> str:
        return self.raw("critical_path_type")

    @property
    def critical_path_drtn_hr_cnt(self) -> float:
        return self.num("critical_drtn_hr_cnt")

    @property
    def calendar_id(self) -> int:
        return int(self.num("clndr_id"))

    @property
    def guid(self) -> str:
        return self.raw("guid")