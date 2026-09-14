"""User Defined Fields (UDF)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity, label_of

if TYPE_CHECKING:
    pass


class UdfType(Entity):
    """One UDFTYPE row - UDF definitions."""

    __slots__ = ()

    @property
    def udf_id(self) -> int:
        return int(self.num("udf_id"))

    @property
    def udf_name(self) -> str:
        return self.raw("udf_name")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def data_type(self) -> str:
        return self.raw("udf_type")

    @property
    def label(self) -> str | None:
        # Map UDF data types to human readable labels
        from p6_mcp.domain.base import UDF_DATA_TYPE

        return label_of(UDF_DATA_TYPE, self.data_type)

    @property
    def guid(self) -> str:
        return self.raw("guid")


class UdfValue(Entity):
    """One UDFVALUE row - UDF values for entities."""

    __slots__ = ()

    @property
    def udf_value_id(self) -> int:
        return int(self.num("udf_value_id"))

    @property
    def udf_id(self) -> int:
        return int(self.num("udf_id"))

    # The entity this UDF value belongs to - could be activity, resource, project, etc.
    # We'll store the raw IDs and let services handle the specific entity type
    @property
    def entity_id(self) -> int:
        return int(self.num("entity_id"))

    @property
    def entity_type(self) -> str:
        return self.raw("entity_type")

    @property
    def value(self) -> str:
        return self.raw("udf_value")

    @property
    def guid(self) -> str:
        return self.raw("guid")
