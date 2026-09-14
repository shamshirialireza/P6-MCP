"""Unit tests for the configuration module."""

import tempfile
from pathlib import Path

from p6_mcp.config import Settings


def test_settings_defaults():
    """Test that settings have sensible defaults."""
    settings = Settings()
    assert settings.default_encoding is None
    assert settings.cache_size == 1000
    assert settings.max_output_bytes == 65536


def test_settings_allowed_dirs():
    """Test allowed directories parsing."""
    settings = Settings(allowed_dirs=[Path("/tmp"), Path("/var/tmp")])
    resolved = settings.resolved_allowed_dirs()
    assert len(resolved) == 2
    assert resolved[0] == Path("/tmp").resolve()
    assert resolved[1] == Path("/var/tmp").resolve()


def test_settings_allowed_dirs_single():
    """Test allowed directories parsing with single directory."""
    settings = Settings(allowed_dirs=[Path("/only/path")])
    resolved = settings.resolved_allowed_dirs()
    assert len(resolved) == 1
    assert resolved[0] == Path("/only/path").resolve()


def test_settings_allowed_dirs_empty():
    """Test allowed directories parsing with empty value."""
    settings = Settings(_env={"P6MCP_ALLOWED_DIRS": ""})
    resolved = settings.resolved_allowed_dirs()
    assert len(resolved) == 1
    assert resolved[0] == Path.cwd().expanduser().resolve()


def test_settings_output_dir():
    """Test output directory resolution."""
    settings = Settings(allowed_dirs=[Path("/tmp"), Path("/var/tmp")], output_dir=Path("/output"))
    assert settings.resolved_output_dir() == Path("/output").resolve()


def test_settings_output_dir_default():
    """Test output directory resolution with default value."""
    settings = Settings(allowed_dirs=[Path("/tmp"), Path("/var/tmp")])
    # Should default to the first allowed directory
    output_dir = settings.resolved_output_dir()
    assert output_dir == Path("/tmp").expanduser().resolve()


def test_settings_env_override(monkeypatch):
    """Test that environment variables override defaults."""
    monkeypatch.setenv("P6MCP_DEFAULT_ENCODING", "utf-8")
    monkeypatch.setenv("P6MCP_CACHE_SIZE", "2000")
    monkeypatch.setenv("P6MCP_MAX_OUTPUT_BYTES", "131072")

    settings = Settings(_env={})  # Read from actual environment
    assert settings.default_encoding == "utf-8"
    assert settings.cache_size == 2000
    assert settings.max_output_bytes == 131072


def test_settings_paths_are_path_objects():
    """Test that resolved paths are Path objects."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        settings = Settings(allowed_dirs=[Path(tmp_dir)], output_dir=Path(tmp_dir) / "output")

        allowed_dirs = settings.resolved_allowed_dirs()
        output_dir = settings.resolved_output_dir()

        assert all(isinstance(d, Path) for d in allowed_dirs)
        assert isinstance(output_dir, Path)
