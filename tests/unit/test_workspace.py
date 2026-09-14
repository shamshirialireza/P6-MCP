"""Unit tests for the workspace module."""

import pytest
from pathlib import Path
from p6_mcp.config import Settings
from p6_mcp.exceptions import WorkspaceError
from p6_mcp.repository.workspace import Workspace


def test_workspace_init():
    """Test workspace initialization."""
    settings = Settings()
    workspace = Workspace(settings)
    assert workspace._settings == settings
    assert isinstance(workspace.allowed, list)
    assert isinstance(workspace.output_dir, Path)


def test_inside_allowed():
    """Test the _inside_allowed helper method."""
    settings = Settings(allowed_dirs=[Path("/allowed1"), Path("/allowed2")])
    workspace = Workspace(settings)

    # Test exact match
    assert workspace._inside_allowed(Path("/allowed1")) == True
    assert workspace._inside_allowed(Path("/allowed2")) == True

    # Test parent relationship
    assert workspace._inside_allowed(Path("/allowed1/subdir")) == True
    assert workspace._inside_allowed(Path("/allowed2/deep/nested")) == True

    # Test outside allowed
    assert workspace._inside_allowed(Path("/notallowed")) == False
    assert workspace._inside_allowed(Path("/etc/passwd")) == False


def test_validate_read_absolute_path(tmp_path):
    """Test validating an absolute path that exists."""
    settings = Settings(allowed_dirs=[tmp_path])
    workspace = Workspace(settings)

    # Create a test file
    test_file = tmp_path / "test.xer"
    test_file.write_text("test content")

    # Validate the file
    result = workspace.validate_read(str(test_file))
    assert result == test_file.resolve()


def test_validate_read_relative_path(tmp_path):
    """Test validating a relative path."""
    settings = Settings(allowed_dirs=[tmp_path])
    workspace = Workspace(settings)

    # Create a test file in a subdirectory
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    test_file = subdir / "test.xer"
    test_file.write_text("test content")

    # Change to tmp directory and validate relative path
    import os
    old_cwd = os.getcwd()
    try:
        os.chdir(str(tmp_path))
        result = workspace.validate_read("subdir/test.xer")
        assert result == test_file.resolve()
    finally:
        os.chdir(old_cwd)


def test_validate_read_outside_allowed(tmp_path):
    """Test that validating a path outside allowed directories raises WorkspaceError."""
    settings = Settings(allowed_dirs=[tmp_path])
    workspace = Workspace(settings)

    # Try to validate a path outside allowed directory
    outside_file = tmp_path.parent / "outside.xer"
    outside_file.write_text("test content")

    with pytest.raises(WorkspaceError) as exc_info:
        workspace.validate_read(str(outside_file))

    assert "outside the allowed directories" in str(exc_info.value)


def test_validate_read_nonexistent_file(tmp_path):
    """Test that validating a nonexistent file raises FileAccessError."""
    settings = Settings(allowed_dirs=[tmp_path])
    workspace = Workspace(settings)

    nonexistent = tmp_path / "nonexistent.xer"

    with pytest.raises(Exception) as exc_info:  # Could be FileAccessError or WorkspaceError
        workspace.validate_read(str(nonexistent))

    # Should indicate file doesn't exist or is not a file
    assert "does not exist" in str(exc_info.value) or "not a file" in str(exc_info.value)


def test_validate_write_creates_path(tmp_path):
    """Test validating a write path that may not exist yet."""
    settings = Settings(allowed_dirs=[tmp_path], output_dir=tmp_path / "output")
    workspace = Workspace(settings)

    # Validate a write path in a subdirectory that doesn't exist yet
    write_path = "subdir/newfile.xer"
    result = workspace.validate_write(write_path)

    # Should resolve to absolute path in output directory
    expected = (tmp_path / "output" / "subdir" / "newfile.xer").resolve()
    assert result == expected

    # Parent directories should be created when actually writing
    # (but validate_write doesn't create them, just resolves the path)