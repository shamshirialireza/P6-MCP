"""Risk management (RISKTYPE, RISK, PROJECTISSUE)."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity, label_of

if TYPE_CHECKING:
    from p6_mcp.parser.reader import Table

class RiskType(Entity):
    """One RISKTYPE row - risk types/categories."""

    __slots__ = ()

    @property
    def risk_type_id(self) -> int:
        return int(self.num("risk_type_id"))

    @property
    def risk_type_name(self) -> str:
        return self.raw("risk_type_name")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def guid(self) -> str:
        return self.raw("guid")


class Risk(Entity):
    """One RISK row - individual risks."""

    __slots__ = ()

    @property
    def risk_id(self) -> int:
        return int(self.num("risk_id"))

    @property
    def risk_type_id(self) -> int:
        return int(self.num("risk_type_id"))

    @property
    def proj_id(self) -> int:
        return int(self.num("proj_id"))

    @property
    def risk_name(self) -> str:
        return self.raw("risk_name")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def probability(self) -> float:
        return self.num("probability")

    @property
    def impact(self) -> float:
        return self.num("impact")

    @property
    def risk_score(self) -> float:
        return self.num("risk_score")

    @property
    def guid(self) -> str:
        return self.raw("guid")


class ProjectIssue(Entity):
    """One PROJISSU row - project issues."""

    __slots__ = ()

    @property
    def issue_id(self) -> int:
        return int(self.num("issue_id"))

    @property
    def proj_id(self) -> int:
        return int(self.num("proj_id"))

    @property
    def issue_name(self) -> str:
        return self.raw("issue_name")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def guid(self) -> str:
        return self.raw("guid")