#!/usr/bin/env python3
"""
Ollama server pool with distributed locking for concurrent access control.
"""

import os
import json
import time
import random
import fcntl
import hashlib
import requests
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from logging_utils import get_logger

logger = get_logger(__name__)


@dataclass
class ServerConfig:
  """Configuration for a single Ollama server."""
  url: str
  max_concurrent: int


class ServerLock:
  """
  File-based lock for a single server slot.

  Uses fcntl.flock for atomic locking and stores metadata in the lock file.
  """

  def __init__(
    self,
    lock_file_path: str,
    server_url: str,
    stage_name: str
  ):
    """
    Initialize server lock.

    Args:
      lock_file_path: Path to lock file
      server_url: URL of the server being locked
      stage_name: Name of the stage acquiring the lock
    """
    self.lock_file_path = lock_file_path
    self.server_url = server_url
    self.stage_name = stage_name
    self.lock_file = None
    self.acquired = False

  def acquire(self) -> bool:
    """
    Attempt to acquire the lock.

    Returns:
      True if lock acquired, False otherwise
    """
    try:
      # Open or create lock file
      self.lock_file = open(self.lock_file_path, 'w')

      # Try to acquire exclusive lock (non-blocking)
      fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

      # Write metadata
      metadata = {
        'pid': os.getpid(),
        'timestamp': time.time(),
        'stage': self.stage_name,
        'server_url': self.server_url
      }
      self.lock_file.write(json.dumps(metadata))
      self.lock_file.flush()

      self.acquired = True
      logger.debug(
        f"Acquired lock on {self.server_url} (lock file: {self.lock_file_path})"
      )
      return True

    except (IOError, OSError) as e:
      # Lock is held by another process
      if self.lock_file:
        self.lock_file.close()
        self.lock_file = None
      return False

  def release(self):
    """Release the lock."""
    if self.acquired and self.lock_file:
      try:
        # Release lock
        fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
        self.lock_file.close()

        # Remove lock file
        if os.path.exists(self.lock_file_path):
          os.remove(self.lock_file_path)

        logger.debug(
          f"Released lock on {self.server_url} (lock file: {self.lock_file_path})"
        )

      except Exception as e:
        logger.warning(f"Error releasing lock {self.lock_file_path}: {e}")

      finally:
        self.lock_file = None
        self.acquired = False

  def __enter__(self):
    """Context manager entry."""
    self.acquire()
    return self

  def __exit__(self, exc_type, exc_val, exc_tb):
    """Context manager exit."""
    self.release()

  @staticmethod
  def is_stale(lock_file_path: str) -> bool:
    """
    Check if a lock file is stale (process no longer exists).

    Args:
      lock_file_path: Path to lock file

    Returns:
      True if lock is stale, False otherwise
    """
    try:
      # Try to open and read the lock file
      with open(lock_file_path, 'r') as f:
        # Try to acquire shared lock to read
        fcntl.flock(f.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)

        # If we can acquire shared lock, file is not exclusively locked
        # (this shouldn't happen if another process holds LOCK_EX)
        content = f.read()
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

        # Parse metadata
        metadata = json.loads(content)
        pid = metadata.get('pid')

        if pid is None:
          return True

        # Check if process exists
        try:
          os.kill(pid, 0)  # Signal 0 doesn't kill, just checks existence
          return False  # Process exists, not stale
        except OSError:
          return True  # Process doesn't exist, stale

    except (IOError, OSError, json.JSONDecodeError):
      # Can't read file or it's locked - assume not stale
      return False


class OllamaServerPool:
  """
  Manages a pool of Ollama servers with concurrent access control.

  Handles:
  - Model availability checking
  - Distributed file-based locking
  - Automatic retry with jitter
  - Stale lock cleanup
  """

  def __init__(
    self,
    servers: List[Dict],
    lock_dir: str,
    retry_wait: float,
    retry_max_attempts: int,
    retry_jitter: float,
    check_models: bool = True
  ):
    """
    Initialize server pool.

    Args:
      servers: List of server configs [{"url": "...", "max_concurrent": 1}, ...]
      lock_dir: Directory for lock files
      retry_wait: Base wait time between retries (seconds)
      retry_max_attempts: Maximum retry attempts
      retry_jitter: Maximum random jitter to add to retry wait (seconds)
      check_models: Whether to check model availability (default: True)
    """
    self.servers = [
      ServerConfig(url=s['url'], max_concurrent=s['max_concurrent'])
      for s in servers
    ]
    self.lock_dir = lock_dir
    self.retry_wait = retry_wait
    self.retry_max_attempts = retry_max_attempts
    self.retry_jitter = retry_jitter
    self.check_models = check_models
    self.active_locks = []  # Track locks acquired by this pool

    # Create lock directory
    os.makedirs(lock_dir, exist_ok=True)

    logger.debug(f"Initialized Ollama server pool with {len(self.servers)} servers")

  def _get_server_hash(self, server_url: str) -> str:
    """Get a short hash for a server URL."""
    return hashlib.md5(server_url.encode()).hexdigest()[:8]

  def _get_lock_file_path(self, server_url: str, slot: int) -> str:
    """Get lock file path for a server slot."""
    server_hash = self._get_server_hash(server_url)
    return os.path.join(self.lock_dir, f"server-{server_hash}-{slot}.lock")

  def _check_model_available(self, server_url: str, model_name: str) -> bool:
    """
    Check if a model is available on a server.

    Args:
      server_url: Base server URL (e.g., "http://localhost:11434")
      model_name: Model name to check

    Returns:
      True if model is available, False otherwise
    """
    # Extract base URL (remove /api/generate if present)
    base_url = server_url.replace('/api/generate', '')
    tags_url = f"{base_url}/api/tags"

    try:
      response = requests.get(tags_url, timeout=5)
      response.raise_for_status()

      data = response.json()
      models = data.get('models', [])

      # Check if model exists in the list
      for model in models:
        model_name_in_list = model.get('name', '')
        # Match exact name or name with :latest
        if model_name_in_list == model_name or model_name_in_list == f"{model_name}:latest":
          return True
        # Also check without tag
        if ':' in model_name and model_name_in_list.split(':')[0] == model_name.split(':')[0]:
          return True

      logger.debug(f"Model {model_name} not found on {server_url}")
      return False

    except Exception as e:
      logger.warning(f"Failed to check models on {server_url}: {e}")
      return False

  def _try_acquire_server(
    self,
    server: ServerConfig,
    stage_name: str
  ) -> Optional[ServerLock]:
    """
    Try to acquire a lock on any available slot for a server.

    Args:
      server: Server configuration
      stage_name: Name of the stage acquiring the lock

    Returns:
      ServerLock if acquired, None otherwise
    """
    # Try each slot
    for slot in range(server.max_concurrent):
      lock_file_path = self._get_lock_file_path(server.url, slot)

      # Check for stale lock and clean up
      if os.path.exists(lock_file_path):
        if ServerLock.is_stale(lock_file_path):
          logger.debug(f"Cleaning up stale lock: {lock_file_path}")
          try:
            os.remove(lock_file_path)
          except OSError:
            pass  # Another process may have removed it

      # Try to acquire lock
      lock = ServerLock(lock_file_path, server.url, stage_name)
      if lock.acquire():
        return lock

    return None

  def acquire_server(
    self,
    model_name: str,
    stage_name: str
  ) -> Tuple[Optional[ServerLock], Optional[str]]:
    """
    Acquire a lock on an available server that supports the model.

    Implements retry with jitter.

    Args:
      model_name: Required model name
      stage_name: Name of the stage acquiring the lock

    Returns:
      Tuple of (ServerLock, server_url) if acquired, (None, None) otherwise
    """
    # Filter servers that support the model
    if self.check_models:
      available_servers = [
        s for s in self.servers
        if self._check_model_available(s.url, model_name)
      ]

      if not available_servers:
        logger.error(
          f"No servers have model {model_name} available. "
          f"Checked {len(self.servers)} servers."
        )
        return None, None

      logger.debug(
        f"Found {len(available_servers)}/{len(self.servers)} servers "
        f"with model {model_name}"
      )
    else:
      available_servers = self.servers

    # Try to acquire a server with retry
    for attempt in range(self.retry_max_attempts):
      # Shuffle server order for load balancing
      servers_to_try = list(available_servers)
      random.shuffle(servers_to_try)

      # Try each server
      for server in servers_to_try:
        lock = self._try_acquire_server(server, stage_name)
        if lock:
          logger.debug(
            f"Acquired server {server.url} for {stage_name} "
            f"(attempt {attempt + 1}/{self.retry_max_attempts})"
          )
          # Track this lock
          self.active_locks.append(lock)
          return lock, server.url

      # All servers busy, wait and retry
      if attempt < self.retry_max_attempts - 1:
        jitter = random.uniform(0, self.retry_jitter)
        wait_time = self.retry_wait + jitter

        logger.debug(
          f"All servers busy, waiting {wait_time:.2f}s before retry "
          f"(attempt {attempt + 1}/{self.retry_max_attempts})"
        )
        time.sleep(wait_time)

    logger.error(
      f"Failed to acquire server for {stage_name} after "
      f"{self.retry_max_attempts} attempts"
    )
    return None, None

  def cleanup_all_locks(self, stage_name: Optional[str] = None):
    """
    Clean up all locks held by current process.

    This releases and removes all locks tracked by this pool instance,
    as well as any stale locks from this process.

    Args:
      stage_name: Optional stage name for logging
    """
    # First, release all tracked active locks
    for lock in self.active_locks:
      try:
        if lock.acquired:
          lock.release()
      except Exception as e:
        logger.warning(f"Error releasing tracked lock: {e}")

    self.active_locks = []

    # Then clean up any remaining lock files from this process
    current_pid = os.getpid()

    try:
      lock_files = [
        f for f in os.listdir(self.lock_dir)
        if f.startswith('server-') and f.endswith('.lock')
      ]

      for lock_file in lock_files:
        lock_path = os.path.join(self.lock_dir, lock_file)

        try:
          # Try to open and acquire shared lock to read
          with open(lock_path, 'r') as f:
            # Try non-blocking shared lock
            try:
              fcntl.flock(f.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
              content = f.read()
              fcntl.flock(f.fileno(), fcntl.LOCK_UN)

              metadata = json.loads(content)

              if metadata.get('pid') == current_pid:
                # This is our lock (not currently held), remove it
                os.remove(lock_path)
                logger.debug(f"Cleaned up lock file: {lock_file}")

            except (IOError, OSError):
              # File is exclusively locked, skip
              pass

        except (IOError, OSError, json.JSONDecodeError, KeyError):
          # Can't read or invalid, skip
          pass

    except Exception as e:
      logger.warning(f"Error during lock cleanup: {e}")


# Global server pool instance
_server_pool = None


def get_server_pool() -> Optional[OllamaServerPool]:
  """Get the global server pool instance."""
  return _server_pool


def initialize_server_pool(
  servers: List[Dict],
  lock_dir: str,
  retry_wait: float,
  retry_max_attempts: int,
  retry_jitter: float,
  check_models: bool = True
) -> OllamaServerPool:
  """
  Initialize the global server pool.

  Args:
    servers: List of server configs
    lock_dir: Directory for lock files
    retry_wait: Base wait time between retries (seconds)
    retry_max_attempts: Maximum retry attempts
    retry_jitter: Maximum random jitter (seconds)
    check_models: Whether to check model availability

  Returns:
    OllamaServerPool instance
  """
  global _server_pool

  _server_pool = OllamaServerPool(
    servers=servers,
    lock_dir=lock_dir,
    retry_wait=retry_wait,
    retry_max_attempts=retry_max_attempts,
    retry_jitter=retry_jitter,
    check_models=check_models
  )

  return _server_pool
