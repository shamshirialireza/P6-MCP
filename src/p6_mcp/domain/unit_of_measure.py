"""Unit of measure (UMEASURE)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity

if TYPE_CHECKING:
    pass


class UnitOfMeasure(Entity):
    """One UMEASURE row - unit of measure definitions."""

    __slots__ = ()

    @property
    def uom_id(self) -> int:
        return int(self.num("uom_id"))

    @property
    def uom_name(self) -> str:
        return self.raw("uom_name")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def abbreviation(self) -> str:
        return self.raw("abbreviation")

    @property
    def guid(self) -> str:
        return self.raw("guid")
