"""Cost accounts (PROJCOST)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity, label_of

if TYPE_CHECKING:
    from p6_mcp.parser.reader import Table

class CostAccount(Entity):
    """One PROJCOST row - cost account definitions."""

    __slots__ = ()

    @property
    def acct_id(self) -> int:
        return int(self.num("acct_id"))

    @property
    def acct_name(self) -> str:
        return self.raw("acct_name")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def guid(self) -> str:
        return self.raw("guid")