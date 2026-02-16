#!/usr/bin/env python3
"""
Stage 02: Parsed - Duplicate Detection

This stage uses TF-IDF search to detect duplicate jokes.
"""

import os
import tempfile
from typing import Tuple, Dict

from stage_processor import StageProcessor
from external_scripts import run_external_script, parse_tfidf_score
from logging_utils import get_logger
import config

logger = get_logger(__name__)


class ParsedProcessor(StageProcessor):
  """
  Process parsed jokes to detect duplicates using TF-IDF search.
  """
  
  def __init__(self):
    """Initialize the ParsedProcessor."""
    super().__init__(
      stage_name="parsed",
      input_stage=config.STAGES["parsed"],
      output_stage=config.STAGES["deduped"],
      reject_stage=config.REJECTS["duplicate"],
      config_module=config
    )
  
  def process_file(
    self, 
    filepath: str, 
    headers: Dict[str, str], 
    content: str
  ) -> Tuple[bool, Dict[str, str], str, str]:
    """
    Process a parsed joke file to check for duplicates.
    
    Args:
      filepath: Path to the joke file
      headers: Dictionary of headers from the joke file
      content: Joke content
      
    Returns:
      Tuple of (success: bool, updated_headers: dict, updated_content: str, reject_reason: str)
    """
    joke_id = headers.get('Joke-ID', 'unknown')
    logger.info(f"Processing file for duplicate detection (Joke-ID: {joke_id})")
    
    # Create temporary file for search_tfidf.py
    temp_file = None
    try:
      # Write content to temporary file
      with tempfile.NamedTemporaryFile(
        mode='w',
        encoding='utf-8',
        delete=False,
        suffix='.txt'
      ) as f:
        temp_file = f.name
        f.write(content)
      
      logger.debug(f"Created temporary file {temp_file} for TF-IDF search")
      
      # Call search_tfidf.py with -1 flag for single-line output
      return_code, stdout, stderr = run_external_script(
        config.SEARCH_TFIDF,
        ['-1','-a', config.SEARCH_TFIDF_DATA_DIR, temp_file]
      )
      
      # Check if script executed successfully
      if return_code != 0:
        error_msg = f"search_tfidf.py failed with return code {return_code}: {stderr}"
        logger.error(error_msg)
        return (False, headers, content, error_msg)
      
      # Parse the duplicate score
      try:
        score, funny_id = parse_tfidf_score(stdout)
        logger.info(f"Duplicate score for Joke-ID {joke_id}: {score}")
      except ValueError as e:
        error_msg = f"Failed to parse TF-IDF score: {e}"
        logger.error(error_msg)
        return (False, headers, content, error_msg)
      
      # Add metadata to headers
      headers['Duplicate-Score'] = str(score) + ' ' + str(funny_id)
      headers['Duplicate-Threshold'] = str(config.DUPLICATE_THRESHOLD)
      
      # Check against threshold
      threshold = config.DUPLICATE_THRESHOLD
      if score >= threshold:
        reject_reason = f"Duplicate score {score} >= threshold {threshold}"
        logger.info(f"Rejecting Joke-ID {joke_id}: {reject_reason}")
        return (False, headers, content, reject_reason)
      
      # Not a duplicate
      logger.info(f"Joke-ID {joke_id} passed duplicate check (score {score} < threshold {threshold})")
      return (True, headers, content, "")
      
    except Exception as e:
      error_msg = f"Unexpected error during duplicate detection: {e}"
      logger.error(error_msg)
      return (False, headers, content, error_msg)
      
    finally:
      # Clean up temporary file
      if temp_file and os.path.exists(temp_file):
        try:
          os.remove(temp_file)
          logger.debug(f"Removed temporary file {temp_file}")
        except Exception as e:
          logger.warning(f"Failed to remove temporary file {temp_file}: {e}")


def main():
  """Main entry point for the stage processor."""
  processor = ParsedProcessor()
  processor.run()


if __name__ == '__main__':
  main()
