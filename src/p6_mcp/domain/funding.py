"""Funding sources (FUNDSRC)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity

if TYPE_CHECKING:
    from p6_mcp.parser.reader import Table

class FundingSource(Entity):
    """One FUNDSRC row - funding source definitions."""

    __slots__ = ()

    @property
    def funding_id(self) -> int:
        return int(self.num("funding_id"))

    @property
    def funding_name(self) -> str:
        return self.raw("funding_name")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def guid(self) -> str:
        return self.raw("guid")