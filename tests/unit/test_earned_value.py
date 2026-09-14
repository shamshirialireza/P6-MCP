"""Unit tests for the earned value analysis module."""

from p6_mcp.services.analysis.earned_value import earned_value


def test_earned_value_import():
    """Test that the earned value module can be imported."""
    assert earned_value is not None


def test_earned_value_function_signature():
    """Test that the earned value function has the expected signature."""
    # This is a basic smoke test - we'll test with actual data in integration tests
    assert callable(earned_value)
