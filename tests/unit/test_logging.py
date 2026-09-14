"""Unit tests for the logging module."""

import logging

from p6_mcp.logging import configure_logging, get_logger


def test_get_logger_returns_logger():
    """Test that get_logger returns a logging.Logger instance."""
    logger = get_logger("test_module")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "p6_mcp.test_module"


def test_get_logger_same_name_returns_same_instance():
    """Test that calling get_logger with same name returns same instance."""
    logger1 = get_logger("test_module")
    logger2 = get_logger("test_module")
    assert logger1 is logger2


def test_configure_logging_sets_level():
    """Test that configure_logging sets the logging level."""
    configure_logging(level="DEBUG")
    root = logging.getLogger("p6_mcp")
    assert root.level == logging.DEBUG


def test_configure_logging_default_level():
    """Test that configure_logging uses INFO as default level."""
    configure_logging()
    root = logging.getLogger("p6_mcp")
    assert root.level == logging.INFO


def test_configure_logging_invalid_level():
    """Test that configure_logging handles invalid level gracefully."""
    # This should not raise an exception
    configure_logging(level="INVALID_LEVEL")
    root = logging.getLogger("p6_mcp")
    # Should fall back to INFO
    assert root.level == logging.INFO
