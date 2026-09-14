"""Thresholds (THRSPARM)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity

if TYPE_CHECKING:
    pass


class ThresholdParameter(Entity):
    """One THRSPARM row - threshold parameters."""

    __slots__ = ()

    @property
    def threshold_id(self) -> int:
        return int(self.num("threshold_id"))

    @property
    def threshold_name(self) -> str:
        return self.raw("threshold_name")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def value(self) -> float:
        return self.num("value")

    @property
    def guid(self) -> str:
        return self.raw("guid")
