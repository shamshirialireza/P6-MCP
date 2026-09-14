"""Documents (DOCUMENT, PROJECTDOCUMENT, ACTIVITYDOCUMENT)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from p6_mcp.domain.base import Entity

if TYPE_CHECKING:
    pass


class DocumentType(Entity):
    """One DOCUMENT row - document types/categories."""

    __slots__ = ()

    @property
    def doc_type_id(self) -> int:
        return int(self.num("doc_type_id"))

    @property
    def doc_type_name(self) -> str:
        return self.raw("doc_type_name")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def guid(self) -> str:
        return self.raw("guid")


class Document(Entity):
    """One DOCUMENT row - documents attached to projects/activities."""

    __slots__ = ()

    @property
    def doc_id(self) -> int:
        return int(self.num("doc_id"))

    @property
    def doc_type_id(self) -> int:
        return int(self.num("doc_type_id"))

    # For project documents
    @property
    def proj_id(self) -> int | None:
        v = self.f("proj_id")
        return int(v) if v is not None else None

    # For activity documents
    @property
    def task_id(self) -> int | None:
        v = self.f("task_id")
        return int(v) if v is not None else None

    @property
    def title(self) -> str:
        return self.raw("title")

    @property
    def description(self) -> str | None:
        v = self.raw("description")
        return v if v else None

    @property
    def file_name(self) -> str:
        return self.raw("file_name")

    @property
    def file_path(self) -> str:
        return self.raw("file_path")

    @property
    def guid(self) -> str:
        return self.raw("guid")
