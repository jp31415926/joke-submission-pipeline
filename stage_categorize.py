#!/usr/bin/env python3
"""
Stage 05: Categorize - Categorization

This stage uses Ollama LLM to assign 1-10 categories to jokes.
"""

import json
from typing import Tuple, Dict, List, Optional

import numpy as np

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

    # Embedding pre-filter setup
    self.prefilter_top_n = config.CATEGORIZE_PREFILTER_TOP_N
    self._embed_model = config.CATEGORIZE_EMBED_MODEL
    self._embed_server_url = config.OLLAMA_SERVERS[0]["url"]
    self._category_embeddings: Optional[np.ndarray] = None  # shape (N, embed_dim)

    try:
      raw = OllamaClient.embed(
        self._embed_model,
        self.valid_categories,
        self._embed_server_url,
      )
      if not isinstance(raw, list) or not raw or not isinstance(raw[0], list):
        raise ValueError(f"Unexpected embedding response type: {type(raw)}")
      self._category_embeddings = np.array(raw, dtype=np.float32)
      self.logger.info(
        f"Pre-computed embeddings for {len(self.valid_categories)} categories "
        f"(shape: {self._category_embeddings.shape})"
      )
    except Exception as e:
      self.logger.warning(
        f"Could not pre-compute category embeddings, pre-filter disabled: {e}"
      )

  def _prefilter_categories(self, content: str, joke_id: str) -> List[str]:
    """
    Return the top-N most semantically similar categories for the given joke.

    Uses cosine similarity between the joke embedding and pre-computed category
    embeddings to narrow the candidate list before sending it to the LLM.
    Falls back to the full valid_categories list if embeddings are unavailable
    or the embed call fails.

    Args:
      content: Joke text to embed
      joke_id: Joke ID for log messages

    Returns:
      List of category strings (at most prefilter_top_n items)
    """
    if self._category_embeddings is None:
      return self.valid_categories

    try:
      raw = OllamaClient.embed(
        self._embed_model, [content], self._embed_server_url
      )
      if not isinstance(raw, list) or not raw or not isinstance(raw[0], list):
        raise ValueError(f"Unexpected joke embedding response type: {type(raw)}")
      joke_vec = np.array(raw[0], dtype=np.float32)

      # Cosine similarity: dot / (||cat|| * ||joke||)
      dot = self._category_embeddings @ joke_vec
      cat_norms = np.linalg.norm(self._category_embeddings, axis=1)
      joke_norm = np.linalg.norm(joke_vec)
      if joke_norm == 0 or np.any(cat_norms == 0):
        return self.valid_categories
      similarities = dot / (cat_norms * joke_norm)

      top_indices = np.argsort(similarities)[::-1][:self.prefilter_top_n]
      selected = [self.valid_categories[i] for i in top_indices]
      self.logger.debug(
        f"{joke_id} Pre-filter: {len(self.valid_categories)} -> "
        f"{len(selected)} categories"
      )
      return selected

    except Exception as e:
      self.logger.warning(
        f"{joke_id} Category pre-filter failed, using full list: {e}"
      )
      return self.valid_categories

  def _validate_categories(
    self,
    categories: List[str],
    joke_id: str = "unknown"
  ) -> Tuple[bool, str, List[str]]:
    """
    Validate and filter category list using exact match only.

    For each LLM category, attempts an exact match (case-insensitive) against
    VALID_CATEGORIES. Categories that do not match are discarded with a warning.
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

    validated = []
    discarded = []

    for cat in categories:
      cat_stripped = cat.strip()
      cat_lower = cat_stripped.lower()

      if cat_lower in valid_categories_lower:
        validated.append(valid_categories_lower[cat_lower])
      else:
        discarded.append(cat_stripped)

    if discarded:
      self.logger.warning(
        f"{joke_id} {len(discarded)} suggested "
        f"categor{'y' if len(discarded) == 1 else 'ies'} not in "
        f"VALID_CATEGORIES (discarded): {discarded}"
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
    candidate_categories = self._prefilter_categories(content, joke_id)
    categories_list_str = ','.join(candidate_categories)
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
