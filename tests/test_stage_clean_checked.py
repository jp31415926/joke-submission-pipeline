#!/usr/bin/env python3
"""
Tests for stage_clean_checked.py - Formatting using LLM.
"""

import os
import sys
import shutil
import tempfile
import pytest
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stage_clean_checked import CleanCheckedProcessor
from file_utils import parse_joke_file
import config


@pytest.fixture
def setup_test_environment():
  """Setup and teardown for each test."""
  # Create temporary directories for testing
  test_dir = tempfile.mkdtemp(prefix="test_clean_checked_")
  pipeline_main = os.path.join(test_dir, "pipeline-main")
  pipeline_priority = os.path.join(test_dir, "pipeline-priority")

  # Create directory structure
  os.makedirs(os.path.join(pipeline_main, "04_clean_checked"))
  os.makedirs(os.path.join(pipeline_main, "05_formatted"))
  os.makedirs(os.path.join(pipeline_main, "53_rejected_format"))

  # Temporarily override config paths
  original_main = config.PIPELINE_MAIN
  original_priority = config.PIPELINE_PRIORITY
  config.PIPELINE_MAIN = pipeline_main
  config.PIPELINE_PRIORITY = pipeline_priority

  yield {
    'test_dir': test_dir,
    'pipeline_main': pipeline_main,
    'input_dir': os.path.join(pipeline_main, "04_clean_checked"),
    'output_dir': os.path.join(pipeline_main, "05_formatted"),
    'reject_dir': os.path.join(pipeline_main, "53_rejected_format")
  }

  # Cleanup
  config.PIPELINE_MAIN = original_main
  config.PIPELINE_PRIORITY = original_priority
  shutil.rmtree(test_dir)


@pytest.fixture
def mock_ollama_high_confidence():
  """Mock Ollama client that returns formatted joke with high confidence."""
  with patch('stage_clean_checked.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.generate.return_value = """
Formatted-Joke: Why did the computer go to the doctor? Because it had a virus! The doctor said, "Take two tablets and call me in the morning."
Confidence: 85
Changes: Fixed capitalization, added proper punctuation, improved sentence structure
"""
    mock_client.parse_structured_response.return_value = {
      'Formatted-Joke': 'Why did the computer go to the doctor? Because it had a virus! The doctor said, "Take two tablets and call me in the morning."',
      'Confidence': '85',
      'Changes': 'Fixed capitalization, added proper punctuation, improved sentence structure'
    }
    mock_client.extract_confidence.return_value = 85
    mock_client_class.return_value = mock_client
    yield mock_client


@pytest.fixture
def mock_ollama_low_confidence():
  """Mock Ollama client that returns formatted joke with low confidence."""
  with patch('stage_clean_checked.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.generate.return_value = """
Formatted-Joke: Why did the computer go to the doctor? Because it had a virus!
Confidence: 50
Changes: Original text was very poor quality, attempted improvements
"""
    mock_client.parse_structured_response.return_value = {
      'Formatted-Joke': 'Why did the computer go to the doctor? Because it had a virus!',
      'Confidence': '50',
      'Changes': 'Original text was very poor quality, attempted improvements'
    }
    mock_client.extract_confidence.return_value = 50
    mock_client_class.return_value = mock_client
    yield mock_client


@pytest.fixture
def mock_ollama_well_formatted():
  """Mock Ollama client for already well-formatted joke."""
  with patch('stage_clean_checked.OllamaClient') as mock_client_class:
    mock_client = Mock()
    formatted_text = 'A mathematician planted a garden. When asked why all the plants were in perfect rows and columns, he replied, "I wanted to see if I could grow square roots."'
    mock_client.generate.return_value = f"""
Formatted-Joke: {formatted_text}
Confidence: 95
Changes: Minimal changes needed, text was already well formatted
"""
    mock_client.parse_structured_response.return_value = {
      'Formatted-Joke': formatted_text,
      'Confidence': '95',
      'Changes': 'Minimal changes needed, text was already well formatted'
    }
    mock_client.extract_confidence.return_value = 95
    mock_client_class.return_value = mock_client
    yield mock_client


def test_poorly_formatted_joke_improved(
  setup_test_environment,
  mock_ollama_high_confidence
):
  """Test that a poorly formatted joke gets improved."""
  env = setup_test_environment

  # Copy poorly formatted joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'poorly_formatted_joke.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'poorly_formatted_joke.txt')
  shutil.copy(source_joke, dest_joke)

  # Run processor
  processor = CleanCheckedProcessor()
  processor.run()

  # Verify file moved to output directory
  output_file = os.path.join(env['output_dir'], 'poorly_formatted_joke.txt')
  assert os.path.exists(output_file)
  assert not os.path.exists(dest_joke)

  # Verify metadata
  headers, content = parse_joke_file(output_file)
  assert headers['Format-Status'] == 'PASS'
  assert headers['Format-Confidence'] == '85'
  assert headers['Pipeline-Stage'] == config.STAGES['formatted']

  # Verify content was updated (not the same as original)
  assert 'Why did the computer go to the doctor?' in content
  assert content != 'why did the computer go to the doctor    because it had a virus!!!'


def test_well_formatted_joke_minimal_changes(
  setup_test_environment,
  mock_ollama_well_formatted
):
  """Test that a well-formatted joke requires minimal changes."""
  env = setup_test_environment

  # Copy well-formatted joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'well_formatted_joke.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'well_formatted_joke.txt')
  shutil.copy(source_joke, dest_joke)

  # Run processor
  processor = CleanCheckedProcessor()
  processor.run()

  # Verify file moved to output directory
  output_file = os.path.join(env['output_dir'], 'well_formatted_joke.txt')
  assert os.path.exists(output_file)

  # Verify metadata
  headers, content = parse_joke_file(output_file)
  assert headers['Format-Status'] == 'PASS'
  assert headers['Format-Confidence'] == '95'


def test_low_confidence_rejected(
  setup_test_environment,
  mock_ollama_low_confidence
):
  """Test that low confidence results in rejection."""
  env = setup_test_environment

  # Copy poorly formatted joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'poorly_formatted_joke.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'poorly_formatted_joke.txt')
  shutil.copy(source_joke, dest_joke)

  # Run processor
  processor = CleanCheckedProcessor()
  processor.run()

  # Verify file moved to reject directory
  reject_file = os.path.join(env['reject_dir'], 'poorly_formatted_joke.txt')
  assert os.path.exists(reject_file)
  assert not os.path.exists(dest_joke)

  # Verify metadata
  headers, content = parse_joke_file(reject_file)
  assert headers['Format-Status'] == 'PASS'
  assert headers['Format-Confidence'] == '50'
  assert headers['Pipeline-Stage'] == config.REJECTS['format']
  assert 'Rejection-Reason' in headers
  assert 'confidence' in headers['Rejection-Reason'].lower()
  assert '50' in headers['Rejection-Reason']


def test_content_updated(
  setup_test_environment,
  mock_ollama_high_confidence
):
  """Test that joke content is actually updated with formatted version."""
  env = setup_test_environment

  # Copy poorly formatted joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'poorly_formatted_joke.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'poorly_formatted_joke.txt')
  shutil.copy(source_joke, dest_joke)

  # Get original content
  original_headers, original_content = parse_joke_file(dest_joke)

  # Run processor
  processor = CleanCheckedProcessor()
  processor.run()

  # Verify content was updated
  output_file = os.path.join(env['output_dir'], 'poorly_formatted_joke.txt')
  headers, formatted_content = parse_joke_file(output_file)

  # Content should be different
  assert formatted_content != original_content

  # Formatted content should be the one from LLM
  assert formatted_content == 'Why did the computer go to the doctor? Because it had a virus! The doctor said, "Take two tablets and call me in the morning."'


def test_metadata_updates(
  setup_test_environment,
  mock_ollama_high_confidence
):
  """Test that metadata fields are updated correctly."""
  env = setup_test_environment

  # Copy joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'poorly_formatted_joke.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'poorly_formatted_joke.txt')
  shutil.copy(source_joke, dest_joke)

  # Run processor
  processor = CleanCheckedProcessor()
  processor.run()

  # Verify metadata
  output_file = os.path.join(env['output_dir'], 'poorly_formatted_joke.txt')
  headers, content = parse_joke_file(output_file)

  # Check required fields
  assert 'Format-Status' in headers
  assert 'Format-Confidence' in headers
  assert headers['Format-Status'] == 'PASS'

  # Confidence should be an integer string
  confidence = int(headers['Format-Confidence'])
  assert 0 <= confidence <= 100


def test_llm_error_handling(setup_test_environment):
  """Test handling of LLM errors."""
  env = setup_test_environment

  # Mock LLM to raise an exception
  with patch('stage_clean_checked.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.generate.side_effect = Exception('LLM connection error')
    mock_client_class.return_value = mock_client

    # Copy joke to input directory
    source_joke = os.path.join(
      os.path.dirname(__file__),
      'fixtures',
      'jokes',
      'poorly_formatted_joke.txt'
    )
    dest_joke = os.path.join(env['input_dir'], 'poorly_formatted_joke.txt')
    shutil.copy(source_joke, dest_joke)

    # Run processor
    processor = CleanCheckedProcessor()
    processor.run()

    # Verify file moved to reject directory due to error
    reject_file = os.path.join(env['reject_dir'], 'poorly_formatted_joke.txt')
    assert os.path.exists(reject_file)

    # Verify rejection reason
    headers, content = parse_joke_file(reject_file)
    assert 'Rejection-Reason' in headers
    assert 'LLM error' in headers['Rejection-Reason']


def test_missing_formatted_joke(setup_test_environment):
  """Test handling when LLM doesn't return formatted joke."""
  env = setup_test_environment

  # Mock LLM to return response without Formatted-Joke field
  with patch('stage_clean_checked.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.generate.return_value = """
Confidence: 85
Changes: Some changes made
"""
    mock_client.parse_structured_response.return_value = {
      'Confidence': '85',
      'Changes': 'Some changes made'
    }
    mock_client.extract_confidence.return_value = 85
    mock_client_class.return_value = mock_client

    # Copy joke to input directory
    source_joke = os.path.join(
      os.path.dirname(__file__),
      'fixtures',
      'jokes',
      'poorly_formatted_joke.txt'
    )
    dest_joke = os.path.join(env['input_dir'], 'poorly_formatted_joke.txt')
    shutil.copy(source_joke, dest_joke)

    # Run processor
    processor = CleanCheckedProcessor()
    processor.run()

    # Verify file moved to reject directory
    reject_file = os.path.join(env['reject_dir'], 'poorly_formatted_joke.txt')
    assert os.path.exists(reject_file)

    # Verify rejection reason
    headers, content = parse_joke_file(reject_file)
    assert 'Rejection-Reason' in headers
    assert 'formatted joke' in headers['Rejection-Reason'].lower()
