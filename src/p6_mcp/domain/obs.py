"""Organizational Breakdown Structure (OBS)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity

if TYPE_CHECKING:
    pass


class ObsType(Entity):
    """One MEMOTYPE row - OBS types."""

    __slots__ = ()

    @property
    def obs_type_id(self) -> int:
        return int(self.num("obs_type_id"))

    @property
    def obs_type_name(self) -> str:
        return self.raw("obs_type_name")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def guid(self) -> str:
        return self.raw("guid")


class Obs(Entity):
    """One OBS row - OBS instances/nodes."""

    __slots__ = ()

    @property
    def obs_id(self) -> int:
        return int(self.num("obs_id"))

    @property
    def obs_type_id(self) -> int:
        return int(self.num("obs_type_id"))

    @property
    def parent_obs_id(self) -> int | None:
        v = self.f("parent_obs_id")
        return int(v) if v is not None else None

    @property
    def obs_name(self) -> str:
        return self.raw("obs_name")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def guid(self) -> str:
        return self.raw("guid")
