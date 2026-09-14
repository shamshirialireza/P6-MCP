"""Currency types (CURRTYPE)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity

if TYPE_CHECKING:
    pass


class Currency(Entity):
    """One CURRTYPE row - currency definitions."""

    __slots__ = ()

    @property
    def curr_id(self) -> int:
        return int(self.num("curr_id"))

    @property
    def curr_name(self) -> str:
        return self.raw("curr_name")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def symbol(self) -> str:
        return self.raw("curr_symbol")

    @property
    def guid(self) -> str:
        return self.raw("guid")
