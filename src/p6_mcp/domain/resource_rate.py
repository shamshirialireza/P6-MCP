"""Resource rates (RSRCRATE)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity

if TYPE_CHECKING:
    pass


class ResourceRate(Entity):
    """One RSRCRATE row - resource rates."""

    __slots__ = ()

    @property
    def rate_id(self) -> int:
        return int(self.num("rate_id"))

    @property
    def resource_id(self) -> int:
        return int(self.num("resource_id"))

    @property
    def role_id(self) -> int | None:
        v = self.f("role_id")
        return int(v) if v is not None else None

    @property
    def effective_date(self) -> datetime | None:
        return self.date("eff_date")

    @property
    def rate_per_hr(self) -> float:
        return self.num("rate_per_hr")

    @property
    def cost_per_hr(self) -> float:
        return self.num("cost_per_hr")

    @property
    def guid(self) -> str:
        return self.raw("guid")
