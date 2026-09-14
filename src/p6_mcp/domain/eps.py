"""Enterprise Project Structure (EPS)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity

if TYPE_CHECKING:
    pass


class EpsNode(Entity):
    """One PROJEPS row - EPS nodes."""

    __slots__ = ()

    @property
    def eps_id(self) -> int:
        return int(self.num("eps_id"))

    @property
    def parent_eps_id(self) -> int | None:
        v = self.f("parent_eps_id")
        return int(v) if v is not None else None

    @property
    def eps_name(self) -> str:
        return self.raw("eps_name")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def guid(self) -> str:
        return self.raw("guid")
