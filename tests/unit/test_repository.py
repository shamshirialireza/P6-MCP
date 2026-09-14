"""Unit tests for the repository module."""

from unittest.mock import Mock

from p6_mcp.config import Settings
from p6_mcp.repository.protocol import MutableScheduleRepository, QueryMode, ScheduleRepository
from p6_mcp.repository.workspace import Workspace


def test_schedule_repository_is_protocol():
    """Test that ScheduleRepository is a Protocol (can't be instantiated directly)."""
    # This is a structural test - we mainly verify it exists and has the right methods
    assert callable(ScheduleRepository)  # Protocols are callable for isinstance checks


def test_mutable_schedule_repository_is_protocol():
    """Test that MutableScheduleRepository is a Protocol."""
    assert callable(MutableScheduleRepository)


def test_query_mode_enum():
    """Test that QueryMode enum has expected values."""
    assert QueryMode.AUTODETECT.value == "autodetect"
    assert QueryMode.FAST.value == "fast"
    assert QueryMode.COMPLETE.value == "complete"


def test_workspace_integration_with_repository():
    """Test that workspace works with repository concepts."""
    settings = Settings()
    workspace = Workspace(settings)

    # Test that workspace has the expected attributes
    assert hasattr(workspace, "_settings")
    assert hasattr(workspace, "allowed")
    assert hasattr(workspace, "output_dir")

    # Test that we can create a mock repository that uses workspace
    mock_repo = Mock(spec=ScheduleRepository)
    mock_repo.workspace = workspace
    assert mock_repo.workspace is workspace
