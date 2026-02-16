#!/usr/bin/env python3
"""
Logging utilities for the joke submission pipeline.
"""

import os
import logging
from typing import Optional

# Global logger instance
_logger = None


def setup_logging(log_dir: str, log_level: str, log_to_stdout: bool = False) -> logging.Logger:
    """
    Setup logging configuration with file and optional console handlers.

    Args:
        log_dir (str): Directory where log files will be stored
        log_level (str): Logging level (e.g., "INFO", "DEBUG")
        log_to_stdout (bool): If True, also log to stdout (default: False)

    Returns:
        logging.Logger: Configured logger instance
    """
    global _logger

    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)

    # Get logger
    logger = logging.getLogger("joke_pipeline")
    logger.setLevel(getattr(logging, log_level.upper()))

    # Remove any existing handlers
    logger.handlers = []

    # Create formatter
    formatter = logging.Formatter(
        #"%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        '%(asctime)s %(levelname)s %(name)s:%(message)s',
        '%Y-%m-%d %H:%M:%S'
    )

    # File handler (always enabled)
    log_file = os.path.join(log_dir, "pipeline.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler (optional)
    if log_to_stdout:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Store reference
    _logger = logger

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance by name. If logging hasn't been set up yet,
    configure with defaults from config.py.

    Args:
        name (str): Name of the logger (will be prefixed with "joke_pipeline.")

    Returns:
        logging.Logger: Logger instance
    """
    global _logger

    if _logger is None:
        # If not configured, setup with defaults
        from config import LOG_DIR, LOG_LEVEL
        setup_logging(LOG_DIR, LOG_LEVEL)

    # Return a child logger of the configured logger
    # This ensures all loggers inherit the handlers and settings
    logger_name = f"joke_pipeline.{name}"
    return logging.getLogger(logger_name)


def log_with_joke_id(logger: logging.Logger, level: int, joke_id: Optional[str], message: str) -> None:
    """
    Log a message with optional Joke-ID prefix.
    
    Args:
        logger (logging.Logger): Logger instance to use
        level (int): Logging level (DEBUG, INFO, WARNING, ERROR)
        joke_id (str or None): Joke ID to prefix message with, or None
        message (str): Message to log
    """
    if joke_id is not None:
        formatted_message = f"[Joke-ID: {joke_id}] {message}"
    else:
        formatted_message = message
    
    logger.log(level, formatted_message)