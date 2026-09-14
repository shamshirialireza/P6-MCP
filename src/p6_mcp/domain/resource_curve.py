"""Resource curves (RSRCCURVDATA)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity

if TYPE_CHECKING:
    pass


class ResourceCurveData(Entity):
    """One RSRCCURVDATA row - resource curve data points."""

    __slots__ = ()

    @property
    def curve_id(self) -> int:
        return int(self.num("curve_id"))

    @property
    def cumulative_quantity(self) -> float:
        return self.num("cumqty")

    @property
    def cumulative_percent(self) -> float:
        return self.num("cumqty_pct")

    @property
    def guid(self) -> str:
        return self.raw("guid")
