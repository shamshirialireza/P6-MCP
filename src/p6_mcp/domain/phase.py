"""Phases (PHASE)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity

if TYPE_CHECKING:
    from p6_mcp.parser.reader import Table

class Phase(Entity):
    """One PHASE row - WBS phases."""

    __slots__ = ()

    @property
    def phase_id(self) -> int:
        return int(self.num("phase_id"))

    @property
    def phase_name(self) -> str:
        return self.raw("phase_name")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def guid(self) -> str:
        return self.raw("guid")