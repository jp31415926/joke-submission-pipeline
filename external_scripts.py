#!/usr/bin/env python3
"""
Utilities for safely calling external scripts and parsing their output.
"""

import os
import subprocess
import logging
from typing import Tuple

from logging_utils import get_logger

logger = get_logger(__name__)


def run_external_script(
  script_path: str,
  args: list,
  timeout: int = None
) -> Tuple[int, str, str]:
  """
  Execute an external script with arguments and capture output.

  Args:
    script_path (str): Path to the script to execute
    args (list): List of arguments to pass to the script
    timeout (int): Timeout in seconds (default: from config.EXTERNAL_SCRIPT_TIMEOUT)

  Returns:
    Tuple[int, str, str]: (return_code, stdout, stderr)

  Raises:
    FileNotFoundError: If script_path doesn't exist
    PermissionError: If script is not executable
    subprocess.TimeoutExpired: If execution exceeds timeout
  """
  # Use config default if timeout not specified
  if timeout is None:
    import config
    timeout = config.EXTERNAL_SCRIPT_TIMEOUT
  # Verify script exists
  if not os.path.exists(script_path):
    logger.error(f"Script not found: {script_path}")
    raise FileNotFoundError(f"Script not found: {script_path}")
  
  # Verify script is executable
  if not os.access(script_path, os.X_OK):
    logger.error(f"Script is not executable: {script_path}")
    raise PermissionError(f"Script is not executable: {script_path}")
  
  # Build command
  command = [script_path] + args
  logger.info(f"Executing external script: {' '.join(command)}")
  
  try:
    # Execute script
    result = subprocess.run(
      command,
      capture_output=True,
      text=True,
      timeout=timeout,
      check=False
    )
    
    # Log result
    logger.info(
      f"Script completed with return code {result.returncode}: {script_path}"
    )
    if result.stderr:
      logger.warning(f"Script stderr: {result.stderr}")
    
    return (result.returncode, result.stdout, result.stderr)
    
  except subprocess.TimeoutExpired as e:
    logger.error(f"Script timed out after {timeout}s: {script_path}")
    raise
  except PermissionError as e:
    logger.error(f"Permission error executing script: {script_path}")
    raise


def parse_tfidf_score(output: str) -> int:
  """
  Parse TF-IDF score from search_tfidf.py output.
  
  Expected format: "91 9278 A Meaningful New Year's Gesture"
  Returns the first integer (the score).
  
  Args:
    output (str): Output from search_tfidf.py
    
  Returns:
    int: TF-IDF score (0-100)
    
  Raises:
    ValueError: If output doesn't match expected format
  """
  if not output or not output.strip():
    raise ValueError("Empty output from TF-IDF script")
  
  # Get first line (in case there's extra output)
  first_line = output.strip().split('\n')[0]
  
  # Split by whitespace
  parts = first_line.split()
  
  if len(parts) < 3:
    raise ValueError(
      f"Invalid TF-IDF output format. Expected: "
      f"'<score> <id> <title>', got: '{first_line}'"
    )
  
  try:
    score = int(parts[0])
  except ValueError:
    raise ValueError(
      f"Invalid TF-IDF score. Expected integer, got: '{parts[0]}'"
    )
  
  # Validate score range
  if score < 0 or score > 100:
    logger.warning(f"TF-IDF score out of expected range (0-100): {score}")
  
  return score
