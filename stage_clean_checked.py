#!/usr/bin/env python3
"""
Stage 04: Clean Checked - Formatting

This stage uses Ollama LLM to improve joke grammar and punctuation.
"""

import json
from typing import Tuple, Dict

from stage_processor import StageProcessor
from ollama_client import OllamaClient
from logging_utils import get_logger
import config

logger = get_logger(__name__)


class CleanCheckedProcessor(StageProcessor):
  """
  Process clean-checked jokes to improve formatting using Ollama LLM.
  """

  def __init__(self):
    """Initialize the CleanCheckedProcessor."""
    super().__init__(
      stage_name="clean_checked",
      input_stage=config.STAGES["clean_checked"],
      output_stage=config.STAGES["formatted"],
      reject_stage=config.REJECTS["format"],
      config_module=config
    )
    self.logger = get_logger("CleanCheckedProcessor")
    self.ollama_client = OllamaClient(config.OLLAMA_FORMATTING)
    self.min_confidence = config.CATEGORIZATION_MIN_CONFIDENCE

  def process_file(
    self,
    filepath: str,
    headers: Dict[str, str],
    content: str
  ) -> Tuple[bool, Dict[str, str], str, str]:
    """
    Process a joke file to improve formatting.

    Args:
      filepath: Path to the joke file
      headers: Dictionary of headers from the joke file
      content: Joke content

    Returns:
      Tuple of (success, updated_headers, updated_content, reject_reason)
    """
    joke_id = headers.get('Joke-ID', 'unknown')
    self.logger.info(f"Processing formatting for Joke-ID: {joke_id}")

    # Construct prompts from config
    system_prompt = self.ollama_client.system_prompt
    user_prompt = self.ollama_client.user_prompt_template.format(content=content)

    try:
      # Call Ollama LLM
      response_text = self.ollama_client.generate(
        system_prompt,
        user_prompt,
        timeout=config.OLLAMA_TIMEOUT
      )

      # Parse JSON response
      try:
        response_dict = json.loads(response_text.strip())
      except json.JSONDecodeError as e:
        self.logger.error(
          f"Failed to parse JSON response for Joke-ID: {joke_id}: {e}"
        )
        # Fall back to old parsing method
        response_dict = self.ollama_client.parse_structured_response(
          response_text,
          ['formatted_joke', 'confidence', 'changes']
        )

      # Extract formatted joke
      formatted_joke = response_dict.get('formatted_joke', '').strip()
      if not formatted_joke:
        error_msg = "LLM did not return formatted joke"
        self.logger.error(f"Joke-ID {joke_id}: {error_msg}")
        return (False, headers, content, error_msg)

      # Extract confidence
      confidence = response_dict.get('confidence')
      if confidence is None:
        confidence = self.ollama_client.extract_confidence(response_dict)
      if confidence is None:
        self.logger.warning(
          f"Could not extract confidence for Joke-ID: {joke_id}, "
          f"using 0"
        )
        confidence = 0

      # Extract changes description
      changes = response_dict.get('changes', 'No changes description provided')

      # Update headers
      headers['Format-Status'] = 'PASS'
      headers['Format-Confidence'] = str(confidence)

      self.logger.info(
        f"Formatting result for Joke-ID {joke_id}: "
        f"Confidence={confidence}, Changes: {changes}"
      )

      # Check confidence threshold
      if confidence < self.min_confidence:
        reject_reason = (
          f"Format confidence {confidence} below minimum "
          f"{self.min_confidence}"
        )
        self.logger.warning(
          f"Joke-ID: {joke_id} rejected due to low format confidence: "
          f"{confidence} < {self.min_confidence}"
        )
        return (False, headers, content, reject_reason)

      # Success - return with formatted content
      self.logger.info(
        f"Joke-ID: {joke_id} formatting complete"
      )
      return (True, headers, formatted_joke, "")

    except Exception as e:
      # Handle LLM errors
      self.logger.error(
        f"LLM error processing Joke-ID: {joke_id}: {e}"
      )
      reject_reason = f"LLM error: {str(e)}"
      return (False, headers, content, reject_reason)


if __name__ == '__main__':
  processor = CleanCheckedProcessor()
  processor.run()
