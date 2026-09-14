"""Role (ROLES row) entity."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity, label_of

if TYPE_CHECKING:
    from p6_mcp.parser.reader import Table

class Role(Entity):
    """One ROLES row with typed accessors."""

    __slots__ = ()

    @property
    def role_id(self) -> int:
        return int(self.num("role_id"))

    @property
    def role_short_name(self) -> str:
        return self.raw("role_short_name")

    @property
    def role_name(self) -> str:
        return self.raw("role_name")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def rate_type(self) -> str:
        return self.raw("rate_type")

    @property
    def default_rate(self) -> float:
        return self.num("default_rate")

    @property
    def default_cost_per_hr(self) -> float:
        return self.num("default_cost_per_hr")

    @property
    def resource_id(self) -> int:
        return int(self.num("resource_id"))

    @property
    def guid(self) -> str:
        return self.raw("guid")