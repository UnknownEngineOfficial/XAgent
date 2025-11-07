"""Tests for logging utilities."""

import pytest
from pathlib import Path
from xagent.utils.logging import get_logger, configure_logging


def test_get_logger():
    """Test getting a logger instance."""
    logger = get_logger("test_module")
    
    assert logger is not None
    # Logger should have basic methods
    assert hasattr(logger, "info")
    assert hasattr(logger, "debug")
    assert hasattr(logger, "warning")
    assert hasattr(logger, "error")


def test_get_logger_different_names():
    """Test getting loggers with different names."""
    logger1 = get_logger("module1")
    logger2 = get_logger("module2")
    
    assert logger1 is not None
    assert logger2 is not None


def test_logger_can_log():
    """Test that logger can actually log messages."""
    logger = get_logger("test")
    
    # These should not raise exceptions
    try:
        logger.info("Test info message")
        logger.debug("Test debug message")
        logger.warning("Test warning message")
        logger.error("Test error message")
    except Exception as e:
        pytest.fail(f"Logger failed to log: {e}")


def test_configure_logging_creates_log_dir(tmp_path, monkeypatch):
    """Test that configure_logging creates logs directory."""
    # Change to temp directory
    monkeypatch.chdir(tmp_path)
    
    # Configure logging
    configure_logging()
    
    # Check that logs directory was created
    log_dir = Path("logs")
    assert log_dir.exists()
    assert log_dir.is_dir()


def test_configure_logging_idempotent(tmp_path, monkeypatch):
    """Test that configure_logging can be called multiple times."""
    monkeypatch.chdir(tmp_path)
    
    # Should not raise exception when called multiple times
    try:
        configure_logging()
        configure_logging()
        configure_logging()
    except Exception as e:
        pytest.fail(f"configure_logging not idempotent: {e}")


def test_logger_after_configuration(tmp_path, monkeypatch):
    """Test getting logger after configuration."""
    monkeypatch.chdir(tmp_path)
    configure_logging()
    
    logger = get_logger("configured_test")
    
    # Should be able to log after configuration
    try:
        logger.info("Test message after configuration")
    except Exception as e:
        pytest.fail(f"Failed to log after configuration: {e}")
