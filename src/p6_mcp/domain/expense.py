"""Expenses (EXPENSE)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity

if TYPE_CHECKING:
    pass


class Expense(Entity):
    """One EXPENSE row - expense definitions."""

    __slots__ = ()

    @property
    def expense_id(self) -> int:
        return int(self.num("expense_id"))

    @property
    def expense_name(self) -> str:
        return self.raw("expense_name")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def guid(self) -> str:
        return self.raw("guid")
