"""Role code types and values."""

from __future__ import annotations

from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity

if TYPE_CHECKING:
    pass


class RoleCodeType(Entity):
    """One ROLECATTYPE row - role code types."""

    __slots__ = ()

    @property
    def code_type_id(self) -> int:
        return int(self.num("code_type_id"))

    @property
    def code_type_name(self) -> str:
        return self.raw("code_type_name")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def guid(self) -> str:
        return self.raw("guid")


class RoleCode(Entity):
    """One ROLECATVAL row - actual values for role code types."""

    __slots__ = ()

    @property
    def code_value_id(self) -> int:
        return int(self.num("code_value_id"))

    @property
    def code_type_id(self) -> int:
        return int(self.num("code_type_id"))

    @property
    def role_id(self) -> int:
        return int(self.num("role_id"))

    @property
    def code_value(self) -> str:
        return self.raw("code_value")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def guid(self) -> str:
        return self.raw("guid")
