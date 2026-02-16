#!/usr/bin/env python3
"""
Utility functions for stage processors.
"""

import sys
import signal

import config
from logging_utils import get_logger
from ollama_server_pool import initialize_server_pool, get_server_pool

logger = get_logger(__name__)


def signal_handler(signum, frame):
  """Handle signals by cleaning up locks."""
  logger.info(f"Received signal {signum}, cleaning up locks...")

  server_pool = get_server_pool()
  if server_pool:
    server_pool.cleanup_all_locks()

  logger.info("Cleanup complete, exiting")
  sys.exit(1)


def initialize_stage_environment():
  """
  Initialize the stage environment.

  Sets up:
  - Ollama server pool
  - Signal handlers for cleanup
  """
  # Initialize Ollama server pool
  logger.info("Initializing Ollama server pool...")
  initialize_server_pool(
    servers=config.OLLAMA_SERVERS,
    lock_dir=config.OLLAMA_LOCK_DIR,
    retry_wait=config.OLLAMA_LOCK_RETRY_WAIT,
    retry_max_attempts=config.OLLAMA_LOCK_RETRY_MAX_ATTEMPTS,
    retry_jitter=config.OLLAMA_LOCK_RETRY_JITTER
  )

  # Register signal handlers for cleanup
  signal.signal(signal.SIGINT, signal_handler)
  signal.signal(signal.SIGTERM, signal_handler)


def cleanup_stage_environment():
  """Clean up the stage environment before exiting."""
  try:
    server_pool = get_server_pool()
    if server_pool:
      server_pool.cleanup_all_locks()
  except Exception as e:
    # Log but don't raise - cleanup is best effort
    logger.warning(f"Error during stage environment cleanup: {e}")
