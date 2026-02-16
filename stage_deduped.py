#!/usr/bin/env python3
"""
Stage 03 - Deduped: Cleanliness check using Ollama LLM.
"""

from typing import Tuple, Dict

from stage_processor import StageProcessor
from ollama_client import OllamaClient
from logging_utils import get_logger
import config


class DedupedProcessor(StageProcessor):
  """
  Process deduped jokes through cleanliness check using LLM.

  This stage:
  - Evaluates jokes for appropriateness using Ollama LLM
  - Adds Cleanliness-Status (PASS/FAIL) header
  - Adds Cleanliness-Confidence (0-100) header
  - Rejects jokes that fail cleanliness or have low confidence
  """

  def __init__(self):
    """Initialize the Deduped processor."""
    super().__init__(
      stage_name="deduped",
      input_stage=config.STAGES["deduped"],
      output_stage=config.STAGES["clean_checked"],
      reject_stage=config.REJECTS["cleanliness"],
      config_module=config
    )
    self.logger = get_logger("DedupedProcessor")
    self.ollama_client = OllamaClient(config.ollama_config)
    self.min_confidence = config.CLEANLINESS_MIN_CONFIDENCE

  def process_file(
    self,
    filepath: str,
    headers: Dict[str, str],
    content: str
  ) -> Tuple[bool, Dict[str, str], str, str]:
    """
    Process a joke file through cleanliness check.

    Args:
      filepath: Path to the joke file
      headers: Dictionary of headers from the joke file
      content: Joke content

    Returns:
      Tuple of (success, updated_headers, updated_content, reject_reason)
    """
    joke_id = headers.get('Joke-ID', 'unknown')
    self.logger.info(f"Processing cleanliness check for Joke-ID: {joke_id}")

    # Construct prompts
    system_prompt = (
      "You are a content moderator evaluating jokes for appropriateness."
    )

    user_prompt = f"""Evaluate this joke for cleanliness and appropriateness:

{content}

Determine if this joke is:
- Clean (no profanity, sexual content, or offensive material)
- Appropriate for general audiences

Respond with:
Status: PASS or FAIL
Confidence: <0-100 integer>
Reason: <brief explanation>
"""

    try:
      # Call Ollama LLM
      response_text = self.ollama_client.generate(
        system_prompt,
        user_prompt
      )

      # Parse response
      response_dict = self.ollama_client.parse_structured_response(
        response_text,
        ['Status', 'Confidence', 'Reason']
      )

      # Extract status
      status = response_dict.get('Status', '').upper()
      if status not in ['PASS', 'FAIL']:
        self.logger.warning(
          f"Invalid status '{status}' for Joke-ID: {joke_id}, "
          f"treating as FAIL"
        )
        status = 'FAIL'

      # Extract confidence
      confidence = self.ollama_client.extract_confidence(response_dict)
      if confidence is None:
        self.logger.warning(
          f"Could not extract confidence for Joke-ID: {joke_id}, "
          f"using 0"
        )
        confidence = 0

      # Extract reason
      reason = response_dict.get('Reason', 'No reason provided')

      # Update headers
      headers['Cleanliness-Status'] = status
      headers['Cleanliness-Confidence'] = str(confidence)

      self.logger.info(
        f"Cleanliness check result for Joke-ID: {joke_id}: "
        f"Status={status}, Confidence={confidence}"
      )

      # Check if failed cleanliness
      if status == 'FAIL':
        reject_reason = f"Cleanliness check failed: {reason}"
        self.logger.warning(
          f"Joke-ID: {joke_id} failed cleanliness check: {reason}"
        )
        return (False, headers, content, reject_reason)

      # Check confidence threshold
      if confidence < self.min_confidence:
        reject_reason = (
          f"Confidence {confidence} below minimum "
          f"{self.min_confidence}: {reason}"
        )
        self.logger.warning(
          f"Joke-ID: {joke_id} rejected due to low confidence: "
          f"{confidence} < {self.min_confidence}"
        )
        return (False, headers, content, reject_reason)

      # Success
      self.logger.info(
        f"Joke-ID: {joke_id} passed cleanliness check"
      )
      return (True, headers, content, "")

    except Exception as e:
      # Handle LLM errors
      self.logger.error(
        f"LLM error processing Joke-ID: {joke_id}: {e}"
      )
      reject_reason = f"LLM error: {str(e)}"
      return (False, headers, content, reject_reason)


if __name__ == '__main__':
  processor = DedupedProcessor()
  processor.run()
