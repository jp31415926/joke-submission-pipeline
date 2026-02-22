#!/usr/bin/env python3
"""
Stage 05: Categorize - Categorization

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


class CategorizeProcessor(StageProcessor):
  """
  Process jokes to assign categories using Ollama LLM.
  """

  def __init__(self):
    """Initialize the CategorizeProcessor."""
    super().__init__(
      stage_name="categorize",
      input_stage=config.STAGES["categorize"],
      output_stage=config.STAGES["title"],
      reject_stage=config.REJECTS["categorize"],
      config_module=config
    )
    self.logger = get_logger("CategorizeProcessor")
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
    Validate and filter category list using exact and near-match logic.

    For each LLM category, attempts matching in this order:
      1. Exact match (case-insensitive)
      2. Strip trailing 'jokes' and retry exact match
      3. LLM category is a substring of an ALLOWED_CAT (shortest match wins)
      4. An ALLOWED_CAT is a substring of the LLM category (shortest match wins)
      5. Discard with a warning

    Near-matches (steps 2-4) are appended after exact matches so they are
    dropped first when the list exceeds MAX_CATEGORIES_PER_JOKE.
    Rejects only if no valid categories remain at all.

    Args:
      categories: List of category strings from the LLM
      joke_id: Joke ID for log messages

    Returns:
      Tuple of (valid: bool, error_message: str, validated_categories: List[str])
    """
    if not categories:
      return (False, "No categories provided", [])

    valid_categories_lower = {cat.lower(): cat for cat in self.valid_categories}

    exact_matches = []
    near_matches = []
    discarded = []

    for cat in categories:
      cat_stripped = cat.strip()
      cat_lower = cat_stripped.lower()

      # Step 1: Exact match (case-insensitive)
      if cat_lower in valid_categories_lower:
        exact_matches.append(valid_categories_lower[cat_lower])
        continue

      # Step 2: Strip trailing 'jokes' and retry exact match
      if cat_lower.endswith('jokes'):
        stripped = cat_lower[:-len('jokes')].strip()
        if stripped in valid_categories_lower:
          matched = valid_categories_lower[stripped]
          near_matches.append(matched)
          self.logger.info(
            f"{joke_id} Near-match (stripped 'jokes'): "
            f"'{cat_stripped}' -> '{matched}'"
          )
          continue

      # Step 3: LLM category is substring of an ALLOWED_CAT
      superstring_of = [
        v for k, v in valid_categories_lower.items() if cat_lower in k
      ]
      if superstring_of:
        matched = min(superstring_of, key=len)
        near_matches.append(matched)
        self.logger.info(
          f"{joke_id} Near-match (substring of allowed): "
          f"'{cat_stripped}' -> '{matched}'"
        )
        continue

      # Step 4: An ALLOWED_CAT is a substring of the LLM category
      substring_of = [
        v for k, v in valid_categories_lower.items() if k in cat_lower
      ]
      if substring_of:
        matched = min(substring_of, key=len)
        near_matches.append(matched)
        self.logger.info(
          f"{joke_id} Near-match (allowed is substring): "
          f"'{cat_stripped}' -> '{matched}'"
        )
        continue

      # Step 5: Discard
      discarded.append(cat_stripped)

    if discarded:
      self.logger.warning(
        f"{joke_id} {len(discarded)} suggested "
        f"categor{'y' if len(discarded) == 1 else 'ies'} not in "
        f"VALID_CATEGORIES (discarded): {discarded}"
      )

    # Exact matches first, near-matches at the end (dropped first if truncated)
    validated = exact_matches + near_matches

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
      headers['Categorize-LLM-Model-Used'] = config.OLLAMA_CATEGORIZATION['OLLAMA_MODEL']

      # Parse JSON response
      try:
        self.logger.debug(f"{joke_id} response: {response_text.replace(chr(10), chr(92) + 'n')}")
        response_dict = json.loads(response_text.strip())
      except json.JSONDecodeError as e:
        self.logger.error(
          f"{joke_id} Failed to parse JSON response: {e}: {response_text.replace(chr(10), chr(92) + 'n')}"
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
      headers['Categorize-Reason'] = reason

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
    processor = CategorizeProcessor()
    processor.run()
  finally:
    cleanup_stage_environment()
