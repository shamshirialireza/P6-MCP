"""Unit tests for the exceptions module."""

import pytest

from p6_mcp.exceptions import (
    AmbiguousMatchError,
    ExportError,
    FileAccessError,
    InvalidArgumentError,
    MutationDisabledError,
    MutationError,
    NotFoundError,
    OptionalDependencyError,
    P6McpError,
    WorkspaceError,
    XerParseError,
)


def test_p6_mcp_error_base():
    """Test that P6McpError is the base exception."""
    assert issubclass(XerParseError, P6McpError)
    assert issubclass(FileAccessError, P6McpError)
    assert issubclass(WorkspaceError, P6McpError)
    assert issubclass(NotFoundError, P6McpError)
    assert issubclass(AmbiguousMatchError, P6McpError)
    assert issubclass(InvalidArgumentError, P6McpError)
    assert issubclass(MutationDisabledError, P6McpError)
    assert issubclass(MutationError, P6McpError)
    assert issubclass(ExportError, P6McpError)
    assert issubclass(OptionalDependencyError, P6McpError)


def test_p6_mcp_error_instantiation():
    """Test that P6McpError can be instantiated."""
    error = P6McpError("Test message")
    assert str(error) == "Test message"
    assert error.message == "Test message"
    assert error.code == "p6mcp_error"
    assert error.hint is None


def test_p6_mcp_error_with_hint():
    """Test that P6McpError can be instantiated with hint."""
    error = P6McpError("Test message", hint="Test hint")
    assert str(error) == "Test message"
    assert error.message == "Test message"
    assert error.hint == "Test hint"


def test_xer_parse_error():
    """Test XerParseError can be raised and caught."""
    with pytest.raises(XerParseError) as exc_info:
        raise XerParseError("Test XER parse error")

    assert "Test XER parse error" in str(exc_info.value)
    assert exc_info.value.code == "xer_parse_error"


def test_file_access_error():
    """Test FileAccessError can be raised and caught."""
    with pytest.raises(FileAccessError) as exc_info:
        raise FileAccessError("Test file access error")

    assert "Test file access error" in str(exc_info.value)
    assert exc_info.value.code == "file_access_error"


def test_workspace_error():
    """Test WorkspaceError can be raised and caught."""
    with pytest.raises(WorkspaceError) as exc_info:
        raise WorkspaceError("Test workspace error")

    assert "Test workspace error" in str(exc_info.value)
    assert exc_info.value.code == "workspace_error"


def test_not_found_error():
    """Test NotFoundError can be raised and caught."""
    with pytest.raises(NotFoundError) as exc_info:
        raise NotFoundError("Resource not found")

    assert "Resource not found" in str(exc_info.value)
    assert exc_info.value.code == "not_found"


def test_invalid_argument_error():
    """Test InvalidArgumentError can be raised and caught."""
    with pytest.raises(InvalidArgumentError) as exc_info:
        raise InvalidArgumentError("Invalid argument")

    assert "Invalid argument" in str(exc_info.value)
    assert exc_info.value.code == "invalid_argument"


def test_mutation_error():
    """Test MutationError can be raised and caught."""
    with pytest.raises(MutationError) as exc_info:
        raise MutationError("Mutation failed")

    assert "Mutation failed" in str(exc_info.value)
    assert exc_info.value.code == "mutation_error"


def test_export_error():
    """Test ExportError can be raised and caught."""
    with pytest.raises(ExportError) as exc_info:
        raise ExportError("Export failed")

    assert "Export failed" in str(exc_info.value)
    assert exc_info.value.code == "export_error"
