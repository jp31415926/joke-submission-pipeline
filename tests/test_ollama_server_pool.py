#!/usr/bin/env python3
"""
Tests for ollama_server_pool.py - Ollama server pool with distributed locking.
"""

import os
import sys
import json
import time
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ollama_server_pool import (
  ServerConfig,
  ServerLock,
  OllamaServerPool,
  initialize_server_pool,
  get_server_pool
)


@pytest.fixture
def temp_lock_dir(tmp_path):
  """Create temporary lock directory."""
  lock_dir = tmp_path / "locks"
  lock_dir.mkdir()
  return str(lock_dir)


@pytest.fixture
def server_configs():
  """Sample server configurations."""
  return [
    {"url": "http://localhost:11434", "max_concurrent": 1},
    {"url": "http://server2:11434", "max_concurrent": 2},
  ]


class TestServerConfig:
  """Tests for ServerConfig dataclass."""

  def test_server_config_creation(self):
    """Test creating a server config."""
    config = ServerConfig(url="http://localhost:11434", max_concurrent=1)
    assert config.url == "http://localhost:11434"
    assert config.max_concurrent == 1


class TestServerLock:
  """Tests for ServerLock class."""

  def test_lock_acquire_and_release(self, temp_lock_dir):
    """Test acquiring and releasing a lock."""
    lock_file = os.path.join(temp_lock_dir, "test.lock")
    lock = ServerLock(
      lock_file_path=lock_file,
      server_url="http://localhost:11434",
      stage_name="test_stage"
    )

    # Acquire lock
    assert lock.acquire() is True
    assert lock.acquired is True
    assert os.path.exists(lock_file)

    # Check lock file content
    with open(lock_file, 'r') as f:
      metadata = json.loads(f.read())
      assert metadata['pid'] == os.getpid()
      assert metadata['stage'] == "test_stage"
      assert metadata['server_url'] == "http://localhost:11434"
      assert 'timestamp' in metadata

    # Release lock
    lock.release()
    assert lock.acquired is False
    assert not os.path.exists(lock_file)

  def test_lock_contention(self, temp_lock_dir):
    """Test that two processes cannot acquire the same lock."""
    lock_file = os.path.join(temp_lock_dir, "test.lock")

    # First lock acquires
    lock1 = ServerLock(lock_file, "http://localhost:11434", "stage1")
    assert lock1.acquire() is True

    # Second lock cannot acquire
    lock2 = ServerLock(lock_file, "http://localhost:11434", "stage2")
    assert lock2.acquire() is False

    # Release first lock
    lock1.release()

    # Now second lock can acquire
    assert lock2.acquire() is True
    lock2.release()

  def test_lock_context_manager(self, temp_lock_dir):
    """Test lock as context manager."""
    lock_file = os.path.join(temp_lock_dir, "test.lock")

    with ServerLock(lock_file, "http://localhost:11434", "test") as lock:
      assert lock.acquired is True
      assert os.path.exists(lock_file)

    # Lock should be released after context
    assert not os.path.exists(lock_file)

  def test_is_stale_nonexistent_file(self, temp_lock_dir):
    """Test stale check on nonexistent file."""
    lock_file = os.path.join(temp_lock_dir, "nonexistent.lock")
    assert ServerLock.is_stale(lock_file) is False

  def test_is_stale_with_dead_process(self, temp_lock_dir):
    """Test stale check with dead process."""
    lock_file = os.path.join(temp_lock_dir, "stale.lock")

    # Create lock file with fake PID
    fake_metadata = {
      'pid': 999999,  # Hopefully nonexistent PID
      'timestamp': time.time(),
      'stage': 'test',
      'server_url': 'http://localhost:11434'
    }

    with open(lock_file, 'w') as f:
      json.dump(fake_metadata, f)

    # Should detect as stale (PID doesn't exist)
    assert ServerLock.is_stale(lock_file) is True

  def test_is_stale_with_current_process(self, temp_lock_dir):
    """Test stale check with current process."""
    lock_file = os.path.join(temp_lock_dir, "current.lock")

    # Create lock file with current PID (not locked)
    metadata = {
      'pid': os.getpid(),
      'timestamp': time.time(),
      'stage': 'test',
      'server_url': 'http://localhost:11434'
    }

    with open(lock_file, 'w') as f:
      json.dump(metadata, f)

    # Should not detect as stale (PID exists and file is not locked)
    assert ServerLock.is_stale(lock_file) is False


class TestOllamaServerPool:
  """Tests for OllamaServerPool class."""

  def test_pool_initialization(self, temp_lock_dir, server_configs):
    """Test pool initialization."""
    pool = OllamaServerPool(
      servers=server_configs,
      lock_dir=temp_lock_dir,
      retry_wait=1.0,
      retry_max_attempts=3,
      retry_jitter=0.5,
      check_models=False
    )

    assert len(pool.servers) == 2
    assert pool.servers[0].url == "http://localhost:11434"
    assert pool.servers[0].max_concurrent == 1
    assert pool.servers[1].url == "http://server2:11434"
    assert pool.servers[1].max_concurrent == 2
    assert pool.lock_dir == temp_lock_dir
    assert pool.retry_wait == 1.0
    assert pool.retry_max_attempts == 3
    assert pool.retry_jitter == 0.5

  def test_get_server_hash(self, temp_lock_dir, server_configs):
    """Test server URL hashing."""
    pool = OllamaServerPool(
      servers=server_configs,
      lock_dir=temp_lock_dir,
      retry_wait=1.0,
      retry_max_attempts=3,
      retry_jitter=0.5,
      check_models=False
    )

    hash1 = pool._get_server_hash("http://localhost:11434")
    hash2 = pool._get_server_hash("http://localhost:11434")
    hash3 = pool._get_server_hash("http://server2:11434")

    # Same URL produces same hash
    assert hash1 == hash2
    # Different URLs produce different hashes
    assert hash1 != hash3
    # Hash is 8 characters
    assert len(hash1) == 8

  def test_get_lock_file_path(self, temp_lock_dir, server_configs):
    """Test lock file path generation."""
    pool = OllamaServerPool(
      servers=server_configs,
      lock_dir=temp_lock_dir,
      retry_wait=1.0,
      retry_max_attempts=3,
      retry_jitter=0.5,
      check_models=False
    )

    path = pool._get_lock_file_path("http://localhost:11434", 0)
    assert path.startswith(temp_lock_dir)
    assert path.endswith("-0.lock")
    assert "server-" in path

  @patch('requests.get')
  def test_check_model_available_success(
    self,
    mock_get,
    temp_lock_dir,
    server_configs
  ):
    """Test checking model availability when model exists."""
    pool = OllamaServerPool(
      servers=server_configs,
      lock_dir=temp_lock_dir,
      retry_wait=1.0,
      retry_max_attempts=3,
      retry_jitter=0.5,
      check_models=False
    )

    # Mock successful response with model
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
      'models': [
        {'name': 'llama3:latest'},
        {'name': 'gemma3:12b'},
      ]
    }
    mock_get.return_value = mock_response

    assert pool._check_model_available(
      "http://localhost:11434",
      "gemma3:12b"
    ) is True
    assert pool._check_model_available(
      "http://localhost:11434",
      "nonexistent"
    ) is False

  @patch('requests.get')
  def test_check_model_available_network_error(
    self,
    mock_get,
    temp_lock_dir,
    server_configs
  ):
    """Test checking model availability with network error."""
    pool = OllamaServerPool(
      servers=server_configs,
      lock_dir=temp_lock_dir,
      retry_wait=1.0,
      retry_max_attempts=3,
      retry_jitter=0.5,
      check_models=False
    )

    # Mock network error
    mock_get.side_effect = Exception("Connection failed")

    assert pool._check_model_available(
      "http://localhost:11434",
      "gemma3:12b"
    ) is False

  def test_try_acquire_server_success(self, temp_lock_dir):
    """Test acquiring a server slot successfully."""
    server_config = ServerConfig(
      url="http://localhost:11434",
      max_concurrent=1
    )

    pool = OllamaServerPool(
      servers=[{"url": server_config.url, "max_concurrent": 1}],
      lock_dir=temp_lock_dir,
      retry_wait=0.1,
      retry_max_attempts=3,
      retry_jitter=0.05,
      check_models=False
    )

    lock = pool._try_acquire_server(server_config, "test_stage")
    assert lock is not None
    assert lock.acquired is True

    # Clean up
    lock.release()

  def test_try_acquire_server_all_busy(self, temp_lock_dir):
    """Test acquiring server when all slots are busy."""
    server_config = ServerConfig(
      url="http://localhost:11434",
      max_concurrent=1
    )

    pool = OllamaServerPool(
      servers=[{"url": server_config.url, "max_concurrent": 1}],
      lock_dir=temp_lock_dir,
      retry_wait=0.1,
      retry_max_attempts=3,
      retry_jitter=0.05,
      check_models=False
    )

    # Acquire the only slot
    lock1 = pool._try_acquire_server(server_config, "stage1")
    assert lock1 is not None

    # Try to acquire again - should fail
    lock2 = pool._try_acquire_server(server_config, "stage2")
    assert lock2 is None

    # Clean up
    lock1.release()

  def test_try_acquire_server_with_stale_lock(self, temp_lock_dir):
    """Test acquiring server with stale lock cleanup."""
    server_config = ServerConfig(
      url="http://localhost:11434",
      max_concurrent=1
    )

    pool = OllamaServerPool(
      servers=[{"url": server_config.url, "max_concurrent": 1}],
      lock_dir=temp_lock_dir,
      retry_wait=0.1,
      retry_max_attempts=3,
      retry_jitter=0.05,
      check_models=False
    )

    # Create stale lock file
    lock_file = pool._get_lock_file_path(server_config.url, 0)
    fake_metadata = {
      'pid': 999999,  # Nonexistent PID
      'timestamp': time.time(),
      'stage': 'old_stage',
      'server_url': server_config.url
    }
    with open(lock_file, 'w') as f:
      json.dump(fake_metadata, f)

    # Should clean up stale lock and acquire
    lock = pool._try_acquire_server(server_config, "test_stage")
    assert lock is not None
    assert lock.acquired is True

    # Clean up
    lock.release()

  @patch('requests.get')
  def test_acquire_server_no_model(
    self,
    mock_get,
    temp_lock_dir,
    server_configs
  ):
    """Test acquiring server when no servers have the model."""
    # Mock response with no matching models
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
      'models': [{'name': 'different-model'}]
    }
    mock_get.return_value = mock_response

    pool = OllamaServerPool(
      servers=server_configs,
      lock_dir=temp_lock_dir,
      retry_wait=0.1,
      retry_max_attempts=2,
      retry_jitter=0.05,
      check_models=True  # Enable model checking
    )

    lock, url = pool.acquire_server("gemma3:12b", "test_stage")
    assert lock is None
    assert url is None

  @patch('requests.get')
  def test_acquire_server_success(
    self,
    mock_get,
    temp_lock_dir,
    server_configs
  ):
    """Test successfully acquiring a server."""
    # Mock response with matching model
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
      'models': [
        {'name': 'gemma3:12b'},
        {'name': 'llama3:latest'},
      ]
    }
    mock_get.return_value = mock_response

    pool = OllamaServerPool(
      servers=server_configs,
      lock_dir=temp_lock_dir,
      retry_wait=0.1,
      retry_max_attempts=2,
      retry_jitter=0.05,
      check_models=True
    )

    lock, url = pool.acquire_server("gemma3:12b", "test_stage")
    assert lock is not None
    assert url in ["http://localhost:11434", "http://server2:11434"]
    assert lock.acquired is True

    # Clean up
    lock.release()

  def test_acquire_server_without_model_check(self, temp_lock_dir, server_configs):
    """Test acquiring server without model checking."""
    pool = OllamaServerPool(
      servers=server_configs,
      lock_dir=temp_lock_dir,
      retry_wait=0.1,
      retry_max_attempts=2,
      retry_jitter=0.05,
      check_models=False  # Disable model checking
    )

    lock, url = pool.acquire_server("any-model", "test_stage")
    assert lock is not None
    assert url is not None
    assert lock.acquired is True

    # Clean up
    lock.release()

  def test_acquire_server_retry(self, temp_lock_dir):
    """Test server acquisition with retry."""
    server_config = [{"url": "http://localhost:11434", "max_concurrent": 1}]

    pool = OllamaServerPool(
      servers=server_config,
      lock_dir=temp_lock_dir,
      retry_wait=0.1,
      retry_max_attempts=3,
      retry_jitter=0.05,
      check_models=False
    )

    # Acquire the only slot
    lock1, _ = pool.acquire_server("test-model", "stage1")
    assert lock1 is not None

    # Try to acquire with retry - should fail after retries
    start_time = time.time()
    lock2, url2 = pool.acquire_server("test-model", "stage2")
    elapsed = time.time() - start_time

    assert lock2 is None
    assert url2 is None
    # Should have waited for retries (at least 2 attempts * 0.1s wait)
    assert elapsed >= 0.2

    # Clean up
    lock1.release()

  def test_cleanup_all_locks(self, temp_lock_dir):
    """Test cleaning up all locks for current process."""
    pool = OllamaServerPool(
      servers=[{"url": "http://localhost:11434", "max_concurrent": 2}],
      lock_dir=temp_lock_dir,
      retry_wait=0.1,
      retry_max_attempts=3,
      retry_jitter=0.05,
      check_models=False
    )

    # Acquire multiple locks
    lock1, _ = pool.acquire_server("model1", "stage1")
    lock2, _ = pool.acquire_server("model2", "stage2")

    assert lock1 is not None
    assert lock2 is not None

    # Create a lock from another process (fake PID)
    other_lock_file = os.path.join(temp_lock_dir, "other-process.lock")
    with open(other_lock_file, 'w') as f:
      json.dump({
        'pid': 999999,
        'timestamp': time.time(),
        'stage': 'other',
        'server_url': 'http://other:11434'
      }, f)

    # Clean up all locks
    pool.cleanup_all_locks()

    # Our locks should be removed
    assert not os.path.exists(lock1.lock_file_path)
    assert not os.path.exists(lock2.lock_file_path)

    # Other process lock should still exist
    assert os.path.exists(other_lock_file)


class TestGlobalServerPool:
  """Tests for global server pool functions."""

  def test_initialize_and_get_server_pool(self, temp_lock_dir, server_configs):
    """Test initializing and getting global server pool."""
    pool = initialize_server_pool(
      servers=server_configs,
      lock_dir=temp_lock_dir,
      retry_wait=1.0,
      retry_max_attempts=5,
      retry_jitter=0.5,
      check_models=False
    )

    assert pool is not None
    assert isinstance(pool, OllamaServerPool)

    # Get the pool
    retrieved_pool = get_server_pool()
    assert retrieved_pool is pool
