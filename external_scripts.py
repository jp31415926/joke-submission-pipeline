#!/usr/bin/env python3
"""Utilities for safely calling external scripts and parsing their output."""

import os
import subprocess
from typing import Tuple
from logging_utils import setup_logger

logger = setup_logger(__name__)


def run_external_script(
  script_path: str,
  args: list,
  timeout: int = 60
) -> Tuple[int, str, str]:
  """
  Execute an external script and capture its output.

  Args:
    script_path: Path to the script to execute
    args: List of arguments to pass to the script
    timeout: Timeout in seconds (default: 60)

  Returns:
    Tuple of (return_code, stdout, stderr)

  Raises:
    FileNotFoundError: If script_path doesn't exist
    PermissionError: If script is not executable
    subprocess.TimeoutExpired: If execution exceeds timeout
  """
  # Verify script exists
  if not os.path.exists(script_path):
    error_msg = f"Script not found: {script_path}"
    logger.error(error_msg)
    raise FileNotFoundError(error_msg)

  # Verify script is executable
  if not os.access(script_path, os.X_OK):
    error_msg = f"Script is not executable: {script_path}"
    logger.error(error_msg)
    raise PermissionError(error_msg)

  # Build command
  command = [script_path] + args
  logger.info(f"Executing command: {' '.join(command)}")

  try:
    # Execute script
    result = subprocess.run(
      command,
      capture_output=True,
      text=True,
      timeout=timeout,
      check=False
    )

    logger.info(
      f"Command completed with return code {result.returncode}"
    )
    if result.stderr:
      logger.warning(f"stderr: {result.stderr}")

    return (result.returncode, result.stdout, result.stderr)

  except subprocess.TimeoutExpired as e:
    error_msg = f"Command timed out after {timeout} seconds"
    logger.error(error_msg)
    raise

  except PermissionError as e:
    error_msg = f"Permission denied executing {script_path}"
    logger.error(error_msg)
    raise


def parse_tfidf_score(output: str) -> int:
  """
  Parse search_tfidf.py output format and extract score.

  Expected format: "91 9278 A Meaningful New Year's Gesture"
  Extracts the first integer (the score).

  Args:
    output: Output string from search_tfidf.py

  Returns:
    Integer score (0-100)

  Raises:
    ValueError: If output doesn't match expected format
  """
  if not output:
    raise ValueError("Empty output - cannot parse score")

  output = output.strip()

  # Split on whitespace and get first token
  parts = output.split()

  if not parts:
    raise ValueError("Empty output after stripping - cannot parse score")

  try:
    score = int(parts[0])
  except (ValueError, IndexError) as e:
    raise ValueError(
      f"Invalid output format - expected integer score at start: {output}"
    )

  # Validate score range
  if not (0 <= score <= 100):
    logger.warning(f"Score {score} outside expected range 0-100")

  return score
