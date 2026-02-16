#!/usr/bin/env python3
"""
Stage 06/07: Categorized/Titled - Title Generation & Final Validation

This stage generates titles for jokes with blank titles and performs
final validation before moving to ready-for-review.
"""

import json
from typing import Tuple, Dict, List

from stage_processor import StageProcessor
from ollama_client import OllamaClient
from logging_utils import get_logger
import config

logger = get_logger(__name__)


class CategorizedProcessor(StageProcessor):
  """
  Process categorized jokes to generate titles (if needed) and validate.
  """

  def __init__(self):
    """Initialize the CategorizedProcessor."""
    super().__init__(
      stage_name="categorized",
      input_stage=config.STAGES["categorized"],
      output_stage=config.STAGES["ready_for_review"],
      reject_stage=config.REJECTS["titled"],
      config_module=config
    )
    self.logger = get_logger("CategorizedProcessor")
    self.ollama_client = OllamaClient(config.OLLAMA_TITLE_GENERATION)
    self.title_min_confidence = config.TITLE_MIN_CONFIDENCE

  def _validate_final(
    self,
    headers: Dict[str, str],
    content: str
  ) -> Tuple[bool, str]:
    """
    Perform final validation before ready-for-review.

    Args:
      headers: Dictionary of headers
      content: Joke content

    Returns:
      Tuple of (valid: bool, error_message: str)
    """
    failures = []

    # Required fields that must exist and not be blank
    required_fields = [
      'Joke-ID',
      'Title',
      'Submitter',
      'Source-Email-File',
      'Pipeline-Stage',
      'Categories'
    ]

    for field in required_fields:
      if field not in headers:
        failures.append(f"Missing required field: {field}")
      elif not headers[field].strip():
        failures.append(f"Blank required field: {field}")

    # Cleanliness-Status must be PASS
    if 'Cleanliness-Status' in headers:
      if headers['Cleanliness-Status'] != 'PASS':
        failures.append(
          f"Cleanliness-Status is {headers['Cleanliness-Status']}, must be PASS"
        )
    else:
      failures.append("Missing Cleanliness-Status field")

    # Format-Status must be PASS
    if 'Format-Status' in headers:
      if headers['Format-Status'] != 'PASS':
        failures.append(
          f"Format-Status is {headers['Format-Status']}, must be PASS"
        )
    else:
      failures.append("Missing Format-Status field")

    # Content must be > 10 characters
    if len(content.strip()) <= 10:
      failures.append(
        f"Content too short: {len(content.strip())} characters (must be > 10)"
      )

    if failures:
      return (False, "; ".join(failures))

    return (True, "")

  def process_file(
    self,
    filepath: str,
    headers: Dict[str, str],
    content: str
  ) -> Tuple[bool, Dict[str, str], str, str]:
    """
    Process a joke file to generate title (if needed) and validate.

    Args:
      filepath: Path to the joke file
      headers: Dictionary of headers from the joke file
      content: Joke content

    Returns:
      Tuple of (success, updated_headers, updated_content, reject_reason)
    """
    joke_id = headers.get('Joke-ID', 'unknown')
    self.logger.info(
      f"Processing title generation and validation for Joke-ID: {joke_id}"
    )

    # Check if title needs to be generated
    title = headers.get('Title', '').strip()

    if not title:
      self.logger.info(f"Joke-ID {joke_id}: Title is blank, generating title")

      # Construct prompts from config
      system_prompt = self.ollama_client.system_prompt
      categories = headers.get('Categories', 'Unknown')
      user_prompt = self.ollama_client.user_prompt_template.format(
        content=content,
        categories=categories
      )

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
            ['title', 'confidence']
          )

        # Extract title
        generated_title = response_dict.get('title', '').strip()
        if not generated_title:
          error_msg = "LLM did not return title"
          self.logger.error(f"Joke-ID {joke_id}: {error_msg}")
          return (False, headers, content, error_msg)

        # Extract confidence
        confidence = response_dict.get('confidence')
        if confidence is None:
          confidence = self.ollama_client.extract_confidence(response_dict)
        if confidence is None:
          self.logger.warning(
            f"Could not extract title confidence for Joke-ID: {joke_id}, "
            f"using 0"
          )
          confidence = 0

        self.logger.info(
          f"Generated title for Joke-ID {joke_id}: '{generated_title}' "
          f"(confidence: {confidence})"
        )

        # Check confidence threshold
        if confidence < self.title_min_confidence:
          reject_reason = (
            f"Title generation confidence {confidence} below minimum "
            f"{self.title_min_confidence}"
          )
          self.logger.warning(
            f"Joke-ID: {joke_id} rejected due to low title confidence"
          )
          return (False, headers, content, reject_reason)

        # Update title in headers
        headers['Title'] = generated_title

      except Exception as e:
        # Handle LLM errors
        error_msg = f"LLM error generating title: {e}"
        self.logger.error(f"Joke-ID {joke_id}: {error_msg}")
        return (False, headers, content, error_msg)

    else:
      self.logger.info(
        f"Joke-ID {joke_id}: Title already exists, skipping generation"
      )

    # Perform final validation
    self.logger.info(f"Performing final validation for Joke-ID: {joke_id}")
    valid, error_message = self._validate_final(headers, content)

    if not valid:
      reject_reason = f"Validation failed: {error_message}"
      self.logger.warning(f"Joke-ID {joke_id}: {reject_reason}")
      return (False, headers, content, reject_reason)

    # Success - ready for review
    self.logger.info(
      f"Joke-ID: {joke_id} passed all validation, ready for review"
    )
    return (True, headers, content, "")


if __name__ == '__main__':
  processor = CategorizedProcessor()
  processor.run()
