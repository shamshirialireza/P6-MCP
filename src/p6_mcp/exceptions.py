"""Exception hierarchy for p6-mcp.

All library errors derive from :class:`P6McpError` and carry a machine-readable
``code`` plus an optional human ``hint`` so the MCP layer can serialize
structured error envelopes without leaking stack traces.
"""

from __future__ import annotations


class P6McpError(Exception):
    """Base error for all p6-mcp failures."""

    code: str = "p6mcp_error"

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint

    def to_dict(self) -> dict[str, object]:
        """Serialize to the structured error envelope used by MCP tools."""
        out: dict[str, object] = {"code": self.code, "message": self.message}
        if self.hint:
            out["hint"] = self.hint
        return out


class XerParseError(P6McpError):
    """The file could not be tokenized/parsed as an XER document."""

    code = "xer_parse_error"


class XerEncodingError(XerParseError):
    """The file's byte encoding could not be determined or decoded."""

    code = "xer_encoding_error"


class FileAccessError(P6McpError):
    """The path does not exist, is not a file, or cannot be read."""

    code = "file_access_error"


class WorkspaceError(P6McpError):
    """The path is outside the allowed workspace directories."""

    code = "workspace_error"


class NotFoundError(P6McpError):
    """A requested entity (project, activity, resource, ...) does not exist."""

    code = "not_found"


class AmbiguousMatchError(P6McpError):
    """An identifier matched more than one entity."""

    code = "ambiguous_match"


class InvalidArgumentError(P6McpError):
    """A tool argument failed validation beyond what the JSON schema covers."""

    code = "invalid_argument"


class MutationDisabledError(P6McpError):
    """A write-back tool was called while mutation is disabled."""

    code = "mutation_disabled"


class MutationError(P6McpError):
    """A write-back operation failed validation or could not be applied."""

    code = "mutation_error"


class ExportError(P6McpError):
    """An export could not be written (bad path, missing optional dependency...)."""

    code = "export_error"


class OptionalDependencyError(P6McpError):
    """A feature requires an optional extra that is not installed."""

    code = "optional_dependency_missing"
