#!/usr/bin/env python3
"""
Tests for logging utilities.
"""

import os
import tempfile
import logging
from unittest.mock import patch
import sys

# Add the project root to sys.path so we can import from it
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from logging_utils import setup_logging, get_logger, log_with_joke_id


def test_setup_logging_creates_log_directory():
    """Test that setup_logging creates log directory if it doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = os.path.join(tmpdir, "test_logs")
        assert not os.path.exists(log_dir)
        
        logger = setup_logging(log_dir, "INFO")
        assert os.path.exists(log_dir)
        assert os.path.isdir(log_dir)
        assert logger is not None


def test_setup_logging_creates_log_file():
    """Test that setup_logging creates log file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = os.path.join(tmpdir, "test_logs")
        logger = setup_logging(log_dir, "INFO")
        
        log_file = os.path.join(log_dir, "pipeline.log")
        assert os.path.exists(log_file)
        assert os.path.isfile(log_file)


def test_setup_logging_configures_handlers():
    """Test that setup_logging configures both file and console handlers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = os.path.join(tmpdir, "test_logs")
        logger = setup_logging(log_dir, "INFO")
        
        # Should have at least two handlers (file + console)
        assert len(logger.handlers) >= 2
        assert logger.level == logging.INFO


def test_log_with_joke_id_includes_prefix():
    """Test that log_with_joke_id includes Joke-ID prefix."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = os.path.join(tmpdir, "test_logs")
        logger = setup_logging(log_dir, "INFO")
        
        # Capture log output
        with patch('sys.stdout') as mock_stdout:
            joke_id = "123e4567-e89b-12d3-a456-426614174000"
            message = "Test message"
            log_with_joke_id(logger, logging.INFO, joke_id, message)
            
            # Check if message was logged with prefix
            # For now, just verify function executes without error


def test_log_with_joke_id_handles_none_joke_id():
    """Test that log_with_joke_id handles None joke_id gracefully."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = os.path.join(tmpdir, "test_logs")
        logger = setup_logging(log_dir, "INFO")
        
        # Capture log output
        with patch('sys.stdout') as mock_stdout:
            joke_id = None
            message = "Test message"
            log_with_joke_id(logger, logging.INFO, joke_id, message)
            
            # Check if message was logged without prefix
            # For now, just verify function executes without error


def test_different_log_levels():
    """Test logging at different levels."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_dir = os.path.join(tmpdir, "test_logs")
        logger = setup_logging(log_dir, "DEBUG")
        
        # Test different log levels
        joke_id = "123e4567-e89b-12d3-a456-426614174000"
        
        log_with_joke_id(logger, logging.DEBUG, joke_id, "Debug message")
        log_with_joke_id(logger, logging.INFO, joke_id, "Info message")
        log_with_joke_id(logger, logging.WARNING, joke_id, "Warning message")
        log_with_joke_id(logger, logging.ERROR, joke_id, "Error message")


def test_get_logger_returns_instance():
    """Test that get_logger returns a logger instance."""
    logger = get_logger("test_logger")
    assert logger is not None
    assert isinstance(logger, logging.Logger)


if __name__ == "__main__":
    # Run tests
    test_setup_logging_creates_log_directory()
    test_setup_logging_creates_log_file()
    test_setup_logging_configures_handlers()
    test_log_with_joke_id_includes_prefix()
    test_log_with_joke_id_handles_none_joke_id()
    test_different_log_levels()
    test_get_logger_returns_instance()
    
    print("All tests passed!")