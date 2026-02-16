#!/usr/bin/env python3
"""
Tests for stage_utils.py - Stage initialization and cleanup utilities.
"""

import os
import sys
import signal
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import stage_utils
from ollama_server_pool import OllamaServerPool


@pytest.fixture
def temp_lock_dir(tmp_path):
  """Create temporary lock directory."""
  lock_dir = tmp_path / "locks"
  lock_dir.mkdir()
  return str(lock_dir)


@pytest.fixture
def mock_config(temp_lock_dir, monkeypatch):
  """Mock config module."""
  mock_config_module = Mock()
  mock_config_module.OLLAMA_SERVERS = [
    {"url": "http://localhost:11434", "max_concurrent": 1}
  ]
  mock_config_module.OLLAMA_LOCK_DIR = temp_lock_dir
  mock_config_module.OLLAMA_LOCK_RETRY_WAIT = 0.1
  mock_config_module.OLLAMA_LOCK_RETRY_MAX_ATTEMPTS = 3
  mock_config_module.OLLAMA_LOCK_RETRY_JITTER = 0.05

  # Patch the config import in stage_utils
  monkeypatch.setattr('stage_utils.config', mock_config_module)
  return mock_config_module


class TestSignalHandler:
  """Tests for signal handler."""

  @patch('stage_utils.get_server_pool')
  @patch('sys.exit')
  def test_signal_handler_with_pool(self, mock_exit, mock_get_pool):
    """Test signal handler cleans up server pool."""
    # Create mock server pool
    mock_pool = Mock(spec=OllamaServerPool)
    mock_pool.cleanup_all_locks = Mock()
    mock_get_pool.return_value = mock_pool

    # Call signal handler
    stage_utils.signal_handler(signal.SIGINT, None)

    # Verify cleanup was called
    mock_pool.cleanup_all_locks.assert_called_once()
    mock_exit.assert_called_once_with(1)

  @patch('stage_utils.get_server_pool')
  @patch('sys.exit')
  def test_signal_handler_without_pool(self, mock_exit, mock_get_pool):
    """Test signal handler when no pool exists."""
    # No server pool
    mock_get_pool.return_value = None

    # Call signal handler - should not crash
    stage_utils.signal_handler(signal.SIGINT, None)

    # Should still exit
    mock_exit.assert_called_once_with(1)

  @patch('stage_utils.get_server_pool')
  @patch('sys.exit')
  def test_signal_handler_with_sigterm(self, mock_exit, mock_get_pool):
    """Test signal handler with SIGTERM."""
    mock_pool = Mock(spec=OllamaServerPool)
    mock_pool.cleanup_all_locks = Mock()
    mock_get_pool.return_value = mock_pool

    # Call with SIGTERM
    stage_utils.signal_handler(signal.SIGTERM, None)

    mock_pool.cleanup_all_locks.assert_called_once()
    mock_exit.assert_called_once_with(1)


class TestInitializeStageEnvironment:
  """Tests for initialize_stage_environment."""

  @patch('stage_utils.initialize_server_pool')
  @patch('signal.signal')
  def test_initialize_stage_environment(
    self,
    mock_signal,
    mock_init_pool,
    mock_config
  ):
    """Test stage environment initialization."""
    # Create mock pool
    mock_pool = Mock(spec=OllamaServerPool)
    mock_init_pool.return_value = mock_pool

    # Initialize environment
    stage_utils.initialize_stage_environment()

    # Verify server pool was initialized with correct params
    mock_init_pool.assert_called_once_with(
      servers=mock_config.OLLAMA_SERVERS,
      lock_dir=mock_config.OLLAMA_LOCK_DIR,
      retry_wait=mock_config.OLLAMA_LOCK_RETRY_WAIT,
      retry_max_attempts=mock_config.OLLAMA_LOCK_RETRY_MAX_ATTEMPTS,
      retry_jitter=mock_config.OLLAMA_LOCK_RETRY_JITTER
    )

    # Verify signal handlers were registered
    assert mock_signal.call_count == 2
    calls = mock_signal.call_args_list

    # Check SIGINT handler
    assert calls[0][0][0] == signal.SIGINT
    assert calls[0][0][1] == stage_utils.signal_handler

    # Check SIGTERM handler
    assert calls[1][0][0] == signal.SIGTERM
    assert calls[1][0][1] == stage_utils.signal_handler

  @patch('stage_utils.initialize_server_pool')
  @patch('signal.signal')
  def test_initialize_stage_environment_integration(
    self,
    mock_signal,
    mock_init_pool,
    mock_config
  ):
    """Test stage environment initialization with real pool."""
    # Initialize environment
    stage_utils.initialize_stage_environment()

    # Should have called initialize_server_pool
    assert mock_init_pool.called


class TestCleanupStageEnvironment:
  """Tests for cleanup_stage_environment."""

  @patch('stage_utils.get_server_pool')
  def test_cleanup_with_pool(self, mock_get_pool):
    """Test cleanup when server pool exists."""
    mock_pool = Mock(spec=OllamaServerPool)
    mock_pool.cleanup_all_locks = Mock()
    mock_get_pool.return_value = mock_pool

    # Clean up
    stage_utils.cleanup_stage_environment()

    # Verify cleanup was called
    mock_pool.cleanup_all_locks.assert_called_once()

  @patch('stage_utils.get_server_pool')
  def test_cleanup_without_pool(self, mock_get_pool):
    """Test cleanup when no server pool exists."""
    mock_get_pool.return_value = None

    # Should not crash
    stage_utils.cleanup_stage_environment()

  @patch('stage_utils.get_server_pool')
  def test_cleanup_with_error(self, mock_get_pool):
    """Test cleanup handles errors gracefully."""
    mock_pool = Mock(spec=OllamaServerPool)
    mock_pool.cleanup_all_locks.side_effect = Exception("Cleanup failed")
    mock_get_pool.return_value = mock_pool

    # Should not raise exception
    try:
      stage_utils.cleanup_stage_environment()
    except Exception:
      pytest.fail("cleanup_stage_environment should not raise exceptions")


class TestIntegration:
  """Integration tests for stage_utils."""

  @patch('signal.signal')
  def test_full_lifecycle(self, mock_signal, mock_config):
    """Test full initialization and cleanup lifecycle."""
    from ollama_server_pool import initialize_server_pool, get_server_pool

    # Initialize
    pool = initialize_server_pool(
      servers=mock_config.OLLAMA_SERVERS,
      lock_dir=mock_config.OLLAMA_LOCK_DIR,
      retry_wait=mock_config.OLLAMA_LOCK_RETRY_WAIT,
      retry_max_attempts=mock_config.OLLAMA_LOCK_RETRY_MAX_ATTEMPTS,
      retry_jitter=mock_config.OLLAMA_LOCK_RETRY_JITTER,
      check_models=False
    )

    assert pool is not None
    assert get_server_pool() is pool

    # Acquire a server
    lock, url = pool.acquire_server("test-model", "test-stage")
    assert lock is not None
    assert url is not None

    # Cleanup should release locks
    stage_utils.cleanup_stage_environment()

    # Lock should be released
    assert not lock.acquired or not os.path.exists(lock.lock_file_path)

  @patch('signal.signal')
  def test_signal_handler_integration(self, mock_signal, mock_config):
    """Test signal handler with real pool."""
    from ollama_server_pool import initialize_server_pool

    # Initialize pool
    pool = initialize_server_pool(
      servers=mock_config.OLLAMA_SERVERS,
      lock_dir=mock_config.OLLAMA_LOCK_DIR,
      retry_wait=0.1,
      retry_max_attempts=3,
      retry_jitter=0.05,
      check_models=False
    )

    # Acquire a lock
    lock, url = pool.acquire_server("test-model", "test-stage")
    assert lock is not None
    lock_file = lock.lock_file_path

    # Simulate signal handler (without actually exiting)
    with patch('sys.exit'):
      stage_utils.signal_handler(signal.SIGINT, None)

    # Lock should be cleaned up
    assert not os.path.exists(lock_file)
