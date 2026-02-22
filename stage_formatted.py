#!/usr/bin/env python3
"""
Stage 05: Formatted - Categorization

This stage uses Ollama LLM to assign 1-10 categories to jokes.
"""

import json
from typing import Tuple, Dict, List

from stage_processor import StageProcessor
from ollama_client import OllamaClient
from logging_utils import get_logger
import config
import joke_categories

logger = get_logger(__name__)


class FormattedProcessor(StageProcessor):
  """
  Process formatted jokes to assign categories using Ollama LLM.
  """

  def __init__(self):
    """Initialize the FormattedProcessor."""
    super().__init__(
      stage_name="formatted",
      input_stage=config.STAGES["formatted"],
      output_stage=config.STAGES["categorized"],
      reject_stage=config.REJECTS["category"],
      config_module=config
    )
    self.logger = get_logger("FormattedProcessor")
    self.ollama_client = OllamaClient(
      config.OLLAMA_CATEGORIZATION,
      stage_name="categorization"
    )
    self.valid_categories = joke_categories.VALID_CATEGORIES
    self.max_categories = joke_categories.MAX_CATEGORIES_PER_JOKE

  def _validate_categories(
    self,
    categories: List[str],
    joke_id: str = "unknown"
  ) -> Tuple[bool, str, List[str]]:
    """
    Validate and filter category list.

    Invalid categories (not in VALID_CATEGORIES) are dropped with a warning.
    If the remaining valid categories exceed MAX_CATEGORIES_PER_JOKE, only the
    first MAX_CATEGORIES_PER_JOKE are kept (the rest are dropped with a warning).
    Rejects only if no valid categories remain after filtering.

    Args:
      categories: List of category strings from the LLM
      joke_id: Joke ID for log messages

    Returns:
      Tuple of (valid: bool, error_message: str, validated_categories: List[str])
    """
    if not categories:
      return (False, "No categories provided", [])

    valid_categories_lower = {cat.lower(): cat for cat in self.valid_categories}

    # Filter out invalid categories, logging a warning for each
    validated = []
    invalid_cats = []
    for cat in categories:
      cat_stripped = cat.strip()
      cat_lower = cat_stripped.lower()
      if cat_lower in valid_categories_lower:
        validated.append(valid_categories_lower[cat_lower])
      else:
        invalid_cats.append(cat_stripped)

    if invalid_cats:
      self.logger.warning(
        f"{joke_id} {len(invalid_cats)} suggested "
        f"categor{'y' if len(invalid_cats) == 1 else 'ies'} not in "
        f"VALID_CATEGORIES (ignored): {invalid_cats}"
      )

    if not validated:
      return (False, "No valid categories after filtering", [])

    # Truncate to max, logging a warning for dropped extras
    if len(validated) > self.max_categories:
      ignored = validated[self.max_categories:]
      validated = validated[:self.max_categories]
      self.logger.warning(
        f"{joke_id} {len(ignored)} categor"
        f"{'y' if len(ignored) == 1 else 'ies'} ignored (exceeds max "
        f"{self.max_categories}): {ignored}"
      )

    return (True, "", validated)

  def process_file(
    self,
    filepath: str,
    headers: Dict[str, str],
    content: str
  ) -> Tuple[bool, Dict[str, str], str, str]:
    """
    Process a joke file to assign categories.

    Args:
      filepath: Path to the joke file
      headers: Dictionary of headers from the joke file
      content: Joke content

    Returns:
      Tuple of (success, updated_headers, updated_content, reject_reason)
    """
    joke_id = headers.get('Joke-ID', 'unknown')
    self.logger.debug(f"{joke_id} Processing categorization")

    # Construct prompts from config
    system_prompt = self.ollama_client.system_prompt
    categories_list_str = ','.join(self.valid_categories)
    user_prompt = self.ollama_client.user_prompt_template.format(
      categories_list=categories_list_str,
      content=content
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
        self.logger.debug(f"{joke_id} response: {response_text.replace('\n', '\\n')}")
        response_dict = json.loads(response_text.strip())
      except json.JSONDecodeError as e:
        self.logger.error(
          f"{joke_id} Failed to parse JSON response: {e}: {response_text.replace('\n', '\\n')}"
        )
        # Fall back to old parsing method
        response_dict = self.ollama_client.parse_structured_response(
          response_text,
          ['categories', 'confidence', 'reason']
        )

      # Extract categories
      categories_raw = response_dict.get('categories', [])
      if isinstance(categories_raw, list):
        categories_list = [cat.strip() for cat in categories_raw]
      elif isinstance(categories_raw, str):
        categories_list = [cat.strip() for cat in categories_raw.split(',')]
      else:
        error_msg = "LLM did not return valid categories"
        self.logger.error(f"{joke_id} {error_msg}")
        return (False, headers, content, error_msg)

      if not categories_list:
        error_msg = "LLM returned empty categories list"
        self.logger.error(f"{joke_id} {error_msg}")
        return (False, headers, content, error_msg)

      # Validate categories
      valid, error_msg, validated_categories = self._validate_categories(
        categories_list, joke_id
      )
      if not valid:
        self.logger.error(f"{joke_id} {error_msg}")
        return (False, headers, content, error_msg)

      # Extract reason
      reason = response_dict.get('reason', 'No reason provided')

      # Update headers
      headers['Categories'] = ', '.join(validated_categories)

      self.logger.info(
        f"{joke_id} Categorization: Categories={validated_categories}, Reason: {reason}"
      )

      # Success
      self.logger.debug(
        f"{joke_id} Categorization complete"
      )
      return (True, headers, content, "")

    except Exception as e:
      # Handle LLM errors
      self.logger.error(
        f"{joke_id} LLM error: {e}"
      )
      reject_reason = f"LLM error: {str(e)}"
      return (False, headers, content, reject_reason)


if __name__ == '__main__':
  from stage_utils import initialize_stage_environment, cleanup_stage_environment

  # Initialize environment (server pool, signal handlers)
  initialize_stage_environment()

  try:
    processor = FormattedProcessor()
    processor.run()
  finally:
    cleanup_stage_environment()
