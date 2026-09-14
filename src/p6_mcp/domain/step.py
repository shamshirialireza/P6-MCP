"""Steps (WBSSTEP)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity

if TYPE_CHECKING:
    pass


class Step(Entity):
    """One WBSSTEP row - WBS steps."""

    __slots__ = ()

    @property
    def step_id(self) -> int:
        return int(self.num("step_id"))

    @property
    def wbs_id(self) -> int:
        return int(self.num("wbs_id"))

    @property
    def step_name(self) -> str:
        return self.raw("step_name")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def guid(self) -> str:
        return self.raw("guid")
