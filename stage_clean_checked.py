#!/usr/bin/env python3
"""
Stage 04: Clean Checked - Formatting

This stage uses Ollama LLM to improve joke grammar and punctuation.
"""

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
    self.ollama_client = OllamaClient(
      config.OLLAMA_FORMATTING,
      stage_name="formatting"
    )
    self.min_confidence = config.CATEGORIZATION_MIN_CONFIDENCE

  def _parse_llm_response(
    self,
    response_text: str
  ) -> Tuple[Dict[str, str], str]:
    """
    Parse an LLM response in header+content format.

    Expected format::

      Confidence: <number>
      Changes: <description>

      <joke content, possibly multi-line with blank lines>

    Args:
      response_text: Raw response text from LLM

    Returns:
      Tuple of (headers_dict, joke_content). joke_content is empty
      string if no blank line separator was found.
    """
    headers = {}
    lines = response_text.strip().splitlines()
    content_start = None

    for i, line in enumerate(lines):
      if line.strip() == '':
        content_start = i + 1
        break
      if ':' in line:
        key, _, value = line.partition(':')
        headers[key.strip()] = value.strip()

    if content_start is None:
      return headers, ''

    content = '\n'.join(lines[content_start:]).strip()
    return headers, content

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
    self.logger.info(f"{joke_id} Processing formatting")

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

      self.logger.debug(f"{joke_id} response: {response_text}")

      # Parse header+content format response
      response_headers, formatted_joke = self._parse_llm_response(response_text)

      # Extract formatted joke
      formatted_joke = formatted_joke.strip()
      if not formatted_joke:
        error_msg = "LLM did not return formatted joke"
        self.logger.error(f"{joke_id} {error_msg}")
        return (False, headers, content, error_msg)

      # Extract confidence
      confidence_str = response_headers.get('Confidence', '')
      try:
        confidence = int(confidence_str)
        if not 0 <= confidence <= 100:
          raise ValueError(f"out of range: {confidence}")
      except (ValueError, TypeError):
        self.logger.warning(
          f"{joke_id} Could not parse confidence '{confidence_str}', using 0"
        )
        confidence = 0

      # Extract changes description
      changes = response_headers.get('Changes', 'No changes description provided')

      # Update headers
      headers['Format-Status'] = 'PASS'
      headers['Format-Confidence'] = str(confidence)

      self.logger.info(
        f"{joke_id} Formatting result: Confidence={confidence}, Changes: {changes}"
      )

      # Check confidence threshold
      if confidence < self.min_confidence:
        reject_reason = (
          f"Format confidence {confidence} below minimum "
          f"{self.min_confidence}"
        )
        self.logger.warning(
          f"{joke_id} Rejected due to low format confidence: "
          f"{confidence} < {self.min_confidence}"
        )
        return (False, headers, content, reject_reason)

      # Success - return with formatted content
      self.logger.info(f"{joke_id} Formatting complete")
      return (True, headers, formatted_joke, "")

    except Exception as e:
      # Handle LLM errors
      self.logger.error(f"{joke_id} LLM error: {e}")
      reject_reason = f"LLM error: {str(e)}"
      return (False, headers, content, reject_reason)


if __name__ == '__main__':
  from stage_utils import initialize_stage_environment, cleanup_stage_environment

  # Initialize environment (server pool, signal handlers)
  initialize_stage_environment()

  try:
    processor = CleanCheckedProcessor()
    processor.run()
  finally:
    cleanup_stage_environment()
