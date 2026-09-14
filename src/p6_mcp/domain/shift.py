"""Shift definitions (SHIFT, SHIFTPER)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity

if TYPE_CHECKING:
    pass


class Shift(Entity):
    """One SHIFT row - shift definitions."""

    __slots__ = ()

    @property
    def shift_id(self) -> int:
        return int(self.num("shift_id"))

    @property
    def shift_name(self) -> str:
        return self.raw("shift_name")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def guid(self) -> str:
        return self.raw("guid")


class ShiftPeriod(Entity):
    """One SHIFTPER row - shift periods within a shift."""

    __slots__ = ()

    @property
    def shift_period_id(self) -> int:
        return int(self.num("shift_period_id"))

    @property
    def shift_id(self) -> int:
        return int(self.num("shift_id"))

    @property
    def day_of_week(self) -> int:
        return int(self.num("day_of_week"))  # 1=Sunday, 2=Monday, etc.

    @property
    def start_time(self) -> str:
        return self.raw("start_time")  # HH:MM format

    @property
    def finish_time(self) -> str:
        return self.raw("finish_time")  # HH:MM format

    @property
    def guid(self) -> str:
        return self.raw("guid")
