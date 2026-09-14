"""Baseline projects (PROJECT where project_flag='N')."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity, label_of

if TYPE_CHECKING:
    from p6_mcp.parser.reader import Table

class BaselineProject(Entity):
    """One PROJECT row where project_flag='N' - baseline project."""

    __slots__ = ()

    @property
    def proj_id(self) -> int:
        return int(self.num("proj_id"))

    @property
    def short_name(self) -> str:
        return self.raw("proj_short_name")

    @property
    def name(self) -> str:
        return self.raw("proj_name")

    @property
    def guid(self) -> str:
        return self.raw("guid")

    # Baseline-specific fields
    @property
    def sum_base_proj_id(self) -> int:
        return int(self.num("sum_base_proj_id"))

    @property
    def orig_proj_id(self) -> int:
        return int(self.num("orig_proj_id"))