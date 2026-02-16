#!/usr/bin/env python3
"""
Ollama LLM client for joke pipeline processing.
"""

import json
import re
import requests
from typing import Dict, Optional, Tuple

from logging_utils import get_logger

logger = get_logger(__name__)


class OllamaClient:
  """Client for interacting with Ollama API."""

  def __init__(self, ollama_config: Dict):
    """
    Initialize Ollama client.

    Args:
      ollama_config: Configuration dictionary from config.py
    """
    self.api_url = ollama_config['ollama_api_url']
    self.model = ollama_config['ollama_model']
    self.prefix_prompt = ollama_config.get('ollama_prefix_prompt', '')
    self.options = ollama_config.get('ollama_options', {})
    self.keep_alive = ollama_config.get('ollama_keep_alive', 0)

  def generate(
    self,
    system_prompt: str,
    user_prompt: str,
    timeout: int = 30
  ) -> str:
    """
    Generate response from Ollama API.

    Args:
      system_prompt: System prompt for the LLM
      user_prompt: User prompt for the LLM
      timeout: Request timeout in seconds

    Returns:
      Response text from LLM

    Raises:
      requests.RequestException: On network errors
      ValueError: On invalid JSON response
      TimeoutError: On timeout
    """
    # Build request body
    request_body = {
      'model': self.model,
      'prompt': user_prompt,
      'system': system_prompt,
      'stream': False,
      'options': self.options,
      'keep_alive': self.keep_alive
    }

    # Log request (truncated)
    logger.info(
      f"Ollama request to {self.api_url} with model {self.model}"
    )
    logger.debug(
      f"System prompt: {system_prompt[:100]}..."
    )
    logger.debug(
      f"User prompt: {user_prompt[:200]}..."
    )

    try:
      # POST to Ollama API
      response = requests.post(
        self.api_url,
        json=request_body,
        timeout=timeout
      )

      # Handle rate limiting
      if response.status_code == 429:
        logger.warning("Rate limited by Ollama API")
        raise requests.RequestException("Rate limited (429)")

      # Raise for other HTTP errors
      response.raise_for_status()

      # Parse JSON response
      try:
        response_data = response.json()
      except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from Ollama: {e}")
        raise ValueError(f"Invalid JSON response: {e}")

      # Extract response text
      if 'response' not in response_data:
        logger.error("Missing 'response' field in Ollama response")
        raise ValueError("Missing 'response' field in response")

      response_text = response_data['response']

      # Log response (truncated)
      logger.info(
        f"Ollama response received ({len(response_text)} chars)"
      )
      logger.debug(
        f"Response: {response_text[:200]}..."
      )

      return response_text

    except requests.Timeout as e:
      logger.error(f"Ollama request timed out after {timeout}s")
      raise TimeoutError(f"Request timed out after {timeout}s")
    except requests.RequestException as e:
      logger.error(f"Network error calling Ollama: {e}")
      raise

  def parse_structured_response(
    self,
    response_text: str,
    expected_keys: list
  ) -> Dict[str, str]:
    """
    Parse structured response from LLM.

    Attempts to parse as JSON first, then falls back to key-value parsing.

    Args:
      response_text: Response text from LLM
      expected_keys: List of expected keys to extract

    Returns:
      Dictionary with extracted values
    """
    result = {}

    # Try parsing as JSON first
    try:
      data = json.loads(response_text)
      if isinstance(data, dict):
        for key in expected_keys:
          # Try exact match first
          if key in data:
            result[key] = str(data[key])
          # Try case-insensitive match
          else:
            for k, v in data.items():
              if k.lower() == key.lower():
                result[key] = str(v)
                break
        logger.debug(f"Parsed JSON response: {result}")
        return result
    except (json.JSONDecodeError, TypeError):
      # Not JSON, fall through to key-value parsing
      pass

    # Parse as key-value pairs (Key: Value format)
    for key in expected_keys:
      # Try to find "Key: Value" pattern (case-insensitive)
      pattern = re.compile(
        rf'^{re.escape(key)}:\s*(.+)$',
        re.IGNORECASE | re.MULTILINE
      )
      match = pattern.search(response_text)
      if match:
        result[key] = match.group(1).strip()

    logger.debug(f"Parsed key-value response: {result}")
    return result

  def extract_confidence(
    self,
    response_dict: Dict[str, str]
  ) -> Optional[int]:
    """
    Extract confidence score from response dictionary.

    Args:
      response_dict: Dictionary parsed from LLM response

    Returns:
      Confidence score (0-100) or None if not found
    """
    # Try various keys
    confidence_keys = ['confidence', 'Confidence', 'score', 'Score']

    for key in confidence_keys:
      if key in response_dict:
        value = response_dict[key]
        try:
          # Parse as integer
          confidence = int(value)

          # Validate range
          if 0 <= confidence <= 100:
            logger.debug(f"Extracted confidence: {confidence}")
            return confidence
          else:
            logger.warning(
              f"Confidence out of range (0-100): {confidence}"
            )
            return None

        except (ValueError, TypeError):
          logger.warning(
            f"Could not parse confidence as integer: {value}"
          )
          return None

    logger.debug("No confidence score found in response")
    return None
