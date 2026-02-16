#!/usr/bin/env python3
"""
Ollama LLM client for joke pipeline processing.
"""

import json
import re
import requests
from typing import Dict, Optional, Tuple

from logging_utils import get_logger
from ollama_server_pool import get_server_pool

logger = get_logger(__name__)


class OllamaClient:
  """Client for interacting with Ollama API."""

  def __init__(self, ollama_config: Dict, stage_name: str = "unknown"):
    """
    Initialize Ollama client.

    Args:
      ollama_config: Configuration dictionary from config.py
      stage_name: Name of the stage using this client (for logging)
    """
    self.stage_name = stage_name
    self.model = ollama_config['OLLAMA_MODEL']
    self.system_prompt = ollama_config.get('OLLAMA_SYSTEM_PROMPT', '')
    self.user_prompt_template = ollama_config.get('OLLAMA_USER_PROMPT', '')
    self.options = ollama_config.get('OLLAMA_OPTIONS', {})
    self.keep_alive = ollama_config.get('OLLAMA_KEEP_ALIVE', '1m')
    self.server_pool = get_server_pool()

  def generate(
    self,
    system_prompt: str,
    user_prompt: str,
    timeout: int = 300
  ) -> str:
    """
    Generate response from Ollama API using server pool.

    Args:
      system_prompt: System prompt for the LLM
      user_prompt: User prompt for the LLM
      timeout: Request timeout in seconds

    Returns:
      Response text from LLM

    Raises:
      requests.RequestException: On network errors
      ValueError: On invalid JSON response or no server available
      TimeoutError: On timeout
    """
    if self.server_pool is None:
      raise ValueError(
        "Server pool not initialized. Call initialize_server_pool() first."
      )

    # Acquire a server from the pool
    lock, server_url = self.server_pool.acquire_server(
      model_name=self.model,
      stage_name=self.stage_name
    )

    if lock is None or server_url is None:
      if lock is None:
        raise ValueError(
          f"No lock file returned for model {self.model}. "
          f"All servers busy or model not found."
        )
      else:
        raise ValueError(
          f"No URL returned for model {self.model}. "
          f"All servers busy or model not found."
        )

    try:
      # Build API URL from server URL
      api_url = server_url
      if not api_url.endswith('/api/generate'):
        api_url = f"{api_url}/api/generate"

      # Build request body
      request_body = {
        'model': self.model,
        'prompt': user_prompt,
        'system': system_prompt,
        'stream': False,
        'think': False,
        'options': self.options,
        'keep_alive': self.keep_alive
      }

      # Log request (truncated)
      logger.info(
        f"Ollama request to {api_url} with model {self.model}"
      )
      logger.debug(
        f"System prompt: {system_prompt[:100]}..."
      )
      logger.debug(
        f"User prompt: {user_prompt}..."
      )

      # POST to Ollama API
      response = requests.post(
        api_url,
        json=request_body,
        headers={'Content-Type': 'application/json'},
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
        f"Response: {response_text}..."
      )

      return response_text

    except requests.Timeout as e:
      logger.error(f"Ollama request timed out after {timeout}s")
      raise TimeoutError(f"Request timed out after {timeout}s")
    except requests.RequestException as e:
      logger.error(f"Network error calling Ollama: {e}")
      raise

    finally:
      # Always release the lock
      lock.release()

  def parse_structured_response(
    self,
    response_text: str,
    expected_keys: list
  ) -> Dict[str, str]:
    """
    Parse structured response from LLM.

    Attempts to parse as JSON first, then falls back to key-value parsing.
    Handles JSON wrapped in markdown code blocks (```json ... ```).

    Args:
      response_text: Response text from LLM
      expected_keys: List of expected keys to extract

    Returns:
      Dictionary with extracted values
    """
    result = {}

    # Strip markdown code blocks if present
    # Handles: ```json\n...\n```, ```JSON\n...\n```, or ```\n...\n```
    cleaned_text = response_text.strip()
    if cleaned_text.startswith('```'):
      # Find the end of the opening fence (first newline after ```)
      first_newline = cleaned_text.find('\n')
      if first_newline != -1:
        # Find the closing fence
        closing_fence = cleaned_text.rfind('```')
        if closing_fence > first_newline:
          # Extract content between fences
          cleaned_text = cleaned_text[first_newline + 1:closing_fence].strip()
          logger.debug("Stripped markdown code block from response")

    # Try parsing as JSON first
    try:
      data = json.loads(cleaned_text)
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
      match = pattern.search(cleaned_text)
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
