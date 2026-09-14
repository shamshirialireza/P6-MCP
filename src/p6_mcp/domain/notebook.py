"""Notebook entries (TASKNOTE, TASKMEMO, PROJECTNOTE, etc)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity

if TYPE_CHECKING:
    from p6_mcp.parser.reader import Table

class Notebook(Entity):
    """One TASKNOTE/TASKMEMO/PROJECTNOTE row - notebook entries."""

    __slots__ = ()

    @property
    def notebook_id(self) -> int:
        return int(self.num("notebook_id"))

    # For task notebooks
    @property
    def task_id(self) -> int | None:
        v = self.f("task_id")
        return int(v) if v is not None else None

    # For project notebooks
    @property
    def proj_id(self) -> int | None:
        v = self.f("proj_id")
        return int(v) if v is not None else None

    @property
    def title(self) -> str:
        return self.raw("title")

    @property
    def text(self) -> str:
        return self.raw("text")

    @property
    def guid(self) -> str:
        return self.raw("guid")