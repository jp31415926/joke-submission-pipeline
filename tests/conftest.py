#!/usr/bin/env python3
"""
Shared pytest fixtures for all tests.
"""

import os
import sys
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from ollama_server_pool import initialize_server_pool


@pytest.fixture(scope="function", autouse=True)
def setup_server_pool(tmp_path_factory):
  """
  Automatically initialize server pool for all tests.

  This fixture runs before each test function and ensures the
  server pool is initialized with test configuration.
  """
  # Create temporary lock directory
  lock_dir = tmp_path_factory.mktemp("locks")

  # Initialize server pool with test settings
  initialize_server_pool(
    servers=[{"url": "http://localhost:11434", "max_concurrent": 1}],
    lock_dir=str(lock_dir),
    retry_wait=0.1,
    retry_max_attempts=3,
    retry_jitter=0.05,
    check_models=False  # Skip model checking for tests
  )

  yield

  # Cleanup is automatic via tmp_path_factory


@pytest.fixture(scope="function", autouse=True)
def cleanup_all_stop():
  """
  Remove ALL_STOP file before each test to prevent interference.

  Tests that need ALL_STOP behavior redirect config.ALL_STOP to a
  temp path, so this fixture only removes the real project-level file.
  """
  if os.path.exists(config.ALL_STOP):
    os.remove(config.ALL_STOP)
  yield
