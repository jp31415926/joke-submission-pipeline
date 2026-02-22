#!/usr/bin/env python3
"""
Tests for stage_format.py - Formatting using LLM.
"""

import os
import sys
import shutil
import tempfile
import pytest
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stage_format import FormatProcessor
from file_utils import parse_joke_file
import config


@pytest.fixture
def setup_test_environment():
  """Setup and teardown for each test."""
  # Create temporary directories for testing
  test_dir = tempfile.mkdtemp(prefix="test_format_")
  pipeline_main = os.path.join(test_dir, "pipeline-main")
  pipeline_priority = os.path.join(test_dir, "pipeline-priority")

  # Create directory structure
  os.makedirs(os.path.join(pipeline_main, "04_format"))
  os.makedirs(os.path.join(pipeline_main, "05_categorize"))
  os.makedirs(os.path.join(pipeline_main, "53_rejected_format"))

  # Temporarily override config paths
  original_main = config.PIPELINE_MAIN
  original_priority = config.PIPELINE_PRIORITY
  config.PIPELINE_MAIN = pipeline_main
  config.PIPELINE_PRIORITY = pipeline_priority

  yield {
    'test_dir': test_dir,
    'pipeline_main': pipeline_main,
    'input_dir': os.path.join(pipeline_main, "04_format"),
    'output_dir': os.path.join(pipeline_main, "05_categorize"),
    'reject_dir': os.path.join(pipeline_main, "53_rejected_format")
  }

  # Cleanup
  config.PIPELINE_MAIN = original_main
  config.PIPELINE_PRIORITY = original_priority
  shutil.rmtree(test_dir)


@pytest.fixture
def mock_ollama_high_confidence():
  """Mock Ollama client that returns formatted joke with high confidence."""
  with patch('stage_format.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.system_prompt = 'You are an editor improving joke formatting and grammar.'
    mock_client.user_prompt_template = 'Improve the grammar of this joke: {content}'
    mock_client.generate.return_value = (
      'Confidence: 85\n'
      'Changes: Fixed capitalization, added proper punctuation, improved sentence structure\n'
      '\n'
      'Why did the computer go to the doctor? Because it had a virus! '
      'The doctor said, "Take two tablets and call me in the morning."'
    )
    mock_client_class.return_value = mock_client
    yield mock_client


@pytest.fixture
def mock_ollama_low_confidence():
  """Mock Ollama client that returns formatted joke with low confidence."""
  with patch('stage_format.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.system_prompt = 'You are an editor improving joke formatting and grammar.'
    mock_client.user_prompt_template = 'Improve the grammar of this joke: {content}'
    mock_client.generate.return_value = (
      'Confidence: 45\n'
      'Changes: Original text was very poor quality, attempted improvements\n'
      '\n'
      'Why did the computer go to the doctor? Because it had a virus!'
    )
    mock_client_class.return_value = mock_client
    yield mock_client


@pytest.fixture
def mock_ollama_well_formatted():
  """Mock Ollama client for already well-formatted joke."""
  with patch('stage_format.OllamaClient') as mock_client_class:
    mock_client = Mock()
    formatted_text = (
      'A mathematician planted a garden. When asked why all the plants were in '
      'perfect rows and columns, he replied, "I wanted to see if I could grow '
      'square roots."'
    )
    mock_client.system_prompt = 'You are an editor improving joke formatting and grammar.'
    mock_client.user_prompt_template = 'Improve the grammar of this joke: {content}'
    mock_client.generate.return_value = (
      'Confidence: 95\n'
      'Changes: Minimal changes needed, text was already well formatted\n'
      '\n'
      f'{formatted_text}'
    )
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
  processor = FormatProcessor()
  processor.run()

  # Verify file moved to output directory
  output_file = os.path.join(env['output_dir'], 'poorly_formatted_joke.txt')
  assert os.path.exists(output_file)
  assert not os.path.exists(dest_joke)

  # Verify metadata
  headers, content = parse_joke_file(output_file)
  assert headers['Format-Status'] == 'PASS'
  assert headers['Format-Confidence'] == '85'
  assert headers['Pipeline-Stage'] == config.STAGES['categorize']

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
  processor = FormatProcessor()
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
  processor = FormatProcessor()
  processor.run()

  # Verify file moved to reject directory
  reject_file = os.path.join(env['reject_dir'], 'poorly_formatted_joke.txt')
  assert os.path.exists(reject_file)
  assert not os.path.exists(dest_joke)

  # Verify metadata
  headers, content = parse_joke_file(reject_file)
  assert headers['Format-Status'] == 'PASS'
  assert headers['Format-Confidence'] == '45'
  assert headers['Pipeline-Stage'] == config.REJECTS['format']
  assert 'Rejection-Reason' in headers
  assert 'confidence' in headers['Rejection-Reason'].lower()
  assert '45' in headers['Rejection-Reason']


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
  processor = FormatProcessor()
  processor.run()

  # Verify content was updated
  output_file = os.path.join(env['output_dir'], 'poorly_formatted_joke.txt')
  headers, formatted_content = parse_joke_file(output_file)

  # Content should be different
  assert formatted_content != original_content

  # Formatted content should be the one from LLM
  assert formatted_content == (
    'Why did the computer go to the doctor? Because it had a virus! '
    'The doctor said, "Take two tablets and call me in the morning."'
  )


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
  processor = FormatProcessor()
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
  assert 'Format-Reason' in headers
  assert 'Format-LLM-Model-Used' in headers


def test_llm_error_handling(setup_test_environment):
  """Test handling of LLM errors."""
  env = setup_test_environment

  # Mock LLM to raise an exception
  with patch('stage_format.OllamaClient') as mock_client_class:
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
    processor = FormatProcessor()
    processor.run()

    # Verify file moved to reject directory due to error
    reject_file = os.path.join(env['reject_dir'], 'poorly_formatted_joke.txt')
    assert os.path.exists(reject_file)

    # Verify rejection reason
    headers, content = parse_joke_file(reject_file)
    assert 'Rejection-Reason' in headers
    assert 'LLM error' in headers['Rejection-Reason']


def test_missing_formatted_joke(setup_test_environment):
  """Test handling when LLM response contains no joke content."""
  env = setup_test_environment

  # Mock LLM to return headers only with no blank line + content
  with patch('stage_format.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.system_prompt = 'You are an editor improving joke formatting and grammar.'
    mock_client.user_prompt_template = 'Improve the grammar of this joke: {content}'
    mock_client.generate.return_value = 'Confidence: 85\nChanges: Some changes made'
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
    processor = FormatProcessor()
    processor.run()

    # Verify file moved to reject directory
    reject_file = os.path.join(env['reject_dir'], 'poorly_formatted_joke.txt')
    assert os.path.exists(reject_file)

    # Verify rejection reason
    headers, content = parse_joke_file(reject_file)
    assert 'Rejection-Reason' in headers
    assert 'formatted joke' in headers['Rejection-Reason'].lower()


def test_multiline_joke_with_blank_lines(setup_test_environment):
  """Test that multi-line jokes with blank lines are preserved correctly."""
  env = setup_test_environment

  # Mock LLM to return multi-line joke with blank lines
  with patch('stage_format.OllamaClient') as mock_client_class:
    mock_client = Mock()
    multiline_joke = '''A teacher asks her class, "What do you want to be when you grow up?"

Little Johnny raises his hand and says, "I want to be a millionaire, have a beautiful girlfriend, give her a Ferrari, an apartment in Paris, a mansion in Beverly Hills, a private jet to fly anywhere, an infinite Visa card, and I want to make love to her three times a day."

The teacher, shocked, doesn't know what to say. She decides not to acknowledge Johnny's answer and continues with the lesson.'''

    mock_client.system_prompt = 'You are an editor improving joke formatting and grammar.'
    mock_client.user_prompt_template = 'Improve the grammar of this joke: {content}'
    mock_client.generate.return_value = (
      'Confidence: 90\n'
      'Changes: Fixed grammar and punctuation\n'
      '\n'
      f'{multiline_joke}'
    )
    mock_client_class.return_value = mock_client

    # Copy joke to input directory
    source_joke = os.path.join(
      os.path.dirname(__file__),
      'fixtures',
      'jokes',
      'multiline_joke.txt'
    )
    dest_joke = os.path.join(env['input_dir'], 'multiline_joke.txt')
    shutil.copy(source_joke, dest_joke)

    # Run processor
    processor = FormatProcessor()
    processor.run()

    # Verify file moved to output directory
    output_file = os.path.join(env['output_dir'], 'multiline_joke.txt')
    assert os.path.exists(output_file)

    # Verify content preserves blank lines
    headers, content = parse_joke_file(output_file)

    # Should have multiple lines
    lines = content.split('\n')
    assert len(lines) > 3, "Multi-line joke should have more than 3 lines"

    # Should have blank lines (empty strings in the list)
    assert '' in lines, "Multi-line joke should contain blank lines"

    # Content should match what LLM returned
    assert content == multiline_joke

    # Verify it's not truncated to just first line
    assert "Little Johnny" in content, "Content should include second paragraph"
    assert "teacher, shocked" in content, "Content should include third paragraph"
