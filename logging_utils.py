#!/usr/bin/env python3
"""
Logging utilities for the joke submission pipeline.
"""

import os
import logging
from typing import Optional

# Global logger instance
_logger = None


def setup_logging(log_dir: str, log_level: str) -> logging.Logger:
    """
    Setup logging configuration with file and console handlers.
    
    Args:
        log_dir (str): Directory where log files will be stored
        log_level (str): Logging level (e.g., "INFO", "DEBUG")
        
    Returns:
        logging.Logger: Configured logger instance
    """
    global _logger
    
    # Create log directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)
    
    # Get logger
    logger = logging.getLogger("joke_pipeline")
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # File handler
    log_file = os.path.join(log_dir, "pipeline.log")
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # Console handler
    console_handler = logging.StreamHandler()
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
        name (str): Name of the logger
        
    Returns:
        logging.Logger: Logger instance
    """
    global _logger
    
    if _logger is not None:
        # We already have a logger set up, so return the requested one
        return logging.getLogger(name)
    
    # If not configured, setup with defaults
    from config import LOG_DIR, LOG_LEVEL
    setup_logging(LOG_DIR, LOG_LEVEL)
    # Return the requested logger (this will get the default named logger 
    # that was just configured)
    return logging.getLogger(name)


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