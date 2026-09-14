"""Financial periods (FINDATES, FINTEMPLATE)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity

if TYPE_CHECKING:
    from p6_mcp.parser.reader import Table

class FinancialPeriod(Entity):
    """One FINDATES row - financial period definitions."""

    __slots__ = ()

    @property
    def period_id(self) -> int:
        return int(self.num("period_id"))

    @property
    def period_name(self) -> str:
        return self.raw("period_name")

    @property
    def start_date(self) -> datetime | None:
        return self.date("start_date")

    @property
    def end_date(self) -> datetime | None:
        return self.date("end_date")

    @property
    def guid(self) -> str:
        return self.raw("guid")


class FinancialPeriodTemplate(Entity):
    """One FINTMPL row - financial period templates."""

    __slots__ = ()

    @property
    def template_id(self) -> int:
        return int(self.num("template_id"))

    @property
    def template_name(self) -> str:
        return self.raw("template_name")

    @property
    def guid(self) -> str:
        return self.raw("guid")