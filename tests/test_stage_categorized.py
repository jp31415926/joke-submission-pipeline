#!/usr/bin/env python3
"""
Tests for stage_categorized.py - Title generation and final validation.
"""

import json
import os
import sys
import shutil
import tempfile
import pytest
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stage_categorized import CategorizedProcessor
from file_utils import parse_joke_file, write_joke_file
import config


@pytest.fixture
def setup_test_environment():
  """Setup and teardown for each test."""
  # Create temporary directories for testing
  test_dir = tempfile.mkdtemp(prefix="test_categorized_")
  pipeline_main = os.path.join(test_dir, "pipeline-main")
  pipeline_priority = os.path.join(test_dir, "pipeline-priority")

  # Create directory structure
  os.makedirs(os.path.join(pipeline_main, "06_categorized"))
  os.makedirs(os.path.join(pipeline_main, "08_ready_for_review"))
  os.makedirs(os.path.join(pipeline_main, "55_rejected_titled"))

  # Temporarily override config paths
  original_main = config.PIPELINE_MAIN
  original_priority = config.PIPELINE_PRIORITY
  config.PIPELINE_MAIN = pipeline_main
  config.PIPELINE_PRIORITY = pipeline_priority

  yield {
    'test_dir': test_dir,
    'pipeline_main': pipeline_main,
    'input_dir': os.path.join(pipeline_main, "06_categorized"),
    'output_dir': os.path.join(pipeline_main, "08_ready_for_review"),
    'reject_dir': os.path.join(pipeline_main, "55_rejected_titled")
  }

  # Cleanup
  config.PIPELINE_MAIN = original_main
  config.PIPELINE_PRIORITY = original_priority
  shutil.rmtree(test_dir)


@pytest.fixture
def mock_ollama_title_generation():
  """Mock Ollama client that generates a title."""
  with patch('stage_categorized.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.system_prompt = 'You are a creative title writer.'
    mock_client.user_prompt_template = 'Create title for: {content}'
    mock_client.generate.return_value = json.dumps({"title": "The Traveling Photon", "confidence": 85})
    mock_client.parse_structured_response.return_value = {
      'title': 'The Traveling Photon',
      'confidence': '85'
    }
    mock_client.extract_confidence.return_value = 85
    mock_client_class.return_value = mock_client
    yield mock_client


@pytest.fixture
def mock_ollama_low_confidence_title():
  """Mock Ollama client that generates low confidence title."""
  with patch('stage_categorized.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.system_prompt = 'You are a creative title writer.'
    mock_client.user_prompt_template = 'Create title for: {content}'
    mock_client.generate.return_value = json.dumps({"title": "Some Title", "confidence": 50})
    mock_client.parse_structured_response.return_value = {
      'title': 'Some Title',
      'confidence': '50'
    }
    mock_client.extract_confidence.return_value = 50
    mock_client_class.return_value = mock_client
    yield mock_client


def test_existing_title_preserved(setup_test_environment):
  """Test that jokes with existing titles skip title generation."""
  env = setup_test_environment

  # Copy complete joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'complete_joke.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'complete_joke.txt')
  shutil.copy(source_joke, dest_joke)

  # Get original title
  original_headers, _ = parse_joke_file(dest_joke)
  original_title = original_headers['Title']

  # Run processor (no mocking needed since title exists)
  processor = CategorizedProcessor()
  processor.run()

  # Verify file moved to output directory
  output_file = os.path.join(env['output_dir'], 'complete_joke.txt')
  assert os.path.exists(output_file)
  assert not os.path.exists(dest_joke)

  # Verify title was preserved
  headers, content = parse_joke_file(output_file)
  assert headers['Title'] == original_title
  assert headers['Pipeline-Stage'] == config.STAGES['ready_for_review']


def test_blank_title_generates(
  setup_test_environment,
  mock_ollama_title_generation
):
  """Test that blank title triggers title generation."""
  env = setup_test_environment

  # Copy blank title joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'blank_title_joke.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'blank_title_joke.txt')
  shutil.copy(source_joke, dest_joke)

  # Run processor
  processor = CategorizedProcessor()
  processor.run()

  # Verify file moved to output directory
  output_file = os.path.join(env['output_dir'], 'blank_title_joke.txt')
  assert os.path.exists(output_file)

  # Verify title was generated
  headers, content = parse_joke_file(output_file)
  assert headers['Title'] == 'The Traveling Photon'
  assert headers['Title'] != ''


def test_low_confidence_title_rejected(
  setup_test_environment,
  mock_ollama_low_confidence_title
):
  """Test that low confidence title generation results in rejection."""
  env = setup_test_environment

  # Copy blank title joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'blank_title_joke.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'blank_title_joke.txt')
  shutil.copy(source_joke, dest_joke)

  # Run processor
  processor = CategorizedProcessor()
  processor.run()

  # Verify file moved to reject directory
  reject_file = os.path.join(env['reject_dir'], 'blank_title_joke.txt')
  assert os.path.exists(reject_file)

  # Verify rejection reason
  headers, content = parse_joke_file(reject_file)
  assert 'Rejection-Reason' in headers
  assert 'confidence' in headers['Rejection-Reason'].lower()
  assert '50' in headers['Rejection-Reason']


def test_validation_all_fields_present(setup_test_environment):
  """Test that validation passes with all required fields."""
  env = setup_test_environment

  # Copy complete joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'complete_joke.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'complete_joke.txt')
  shutil.copy(source_joke, dest_joke)

  # Run processor
  processor = CategorizedProcessor()
  processor.run()

  # Verify file moved to output directory
  output_file = os.path.join(env['output_dir'], 'complete_joke.txt')
  assert os.path.exists(output_file)
  assert not os.path.exists(dest_joke)


def test_validation_missing_fields(setup_test_environment):
  """Test that validation fails with missing required fields."""
  env = setup_test_environment

  # Copy incomplete joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'incomplete_joke.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'incomplete_joke.txt')
  shutil.copy(source_joke, dest_joke)

  # Run processor
  processor = CategorizedProcessor()
  processor.run()

  # Verify file moved to reject directory
  reject_file = os.path.join(env['reject_dir'], 'incomplete_joke.txt')
  assert os.path.exists(reject_file)

  # Verify rejection reason mentions validation
  headers, content = parse_joke_file(reject_file)
  assert 'Rejection-Reason' in headers
  assert 'validation' in headers['Rejection-Reason'].lower()


def test_validation_blank_joke_id(setup_test_environment):
  """Test that validation fails with blank Joke-ID."""
  env = setup_test_environment

  # Create joke with blank Joke-ID
  headers = {
    'Joke-ID': '',  # Blank
    'Title': 'Test Title',
    'Submitter': 'test@example.com',
    'Source-Email-File': 'test.txt',
    'Pipeline-Stage': '06_categorized',
    'Cleanliness-Status': 'PASS',
    'Format-Status': 'PASS',
    'Categories': 'Puns'
  }
  content = 'This is a test joke with more than 10 characters.'

  dest_joke = os.path.join(env['input_dir'], 'blank_id.txt')
  write_joke_file(dest_joke, headers, content)

  # Run processor
  processor = CategorizedProcessor()
  processor.run()

  # Verify file moved to reject directory
  reject_file = os.path.join(env['reject_dir'], 'blank_id.txt')
  assert os.path.exists(reject_file)

  # Verify rejection reason
  headers, content = parse_joke_file(reject_file)
  assert 'Rejection-Reason' in headers
  assert 'joke-id' in headers['Rejection-Reason'].lower()


def test_validation_blank_title(setup_test_environment):
  """Test that validation fails with blank title after generation."""
  env = setup_test_environment

  # Mock LLM to return empty title
  with patch('stage_categorized.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.generate.return_value = """
Title:
Confidence: 85
"""
    mock_client.parse_structured_response.return_value = {
      'Title': '',
      'Confidence': '85'
    }
    mock_client.extract_confidence.return_value = 85
    mock_client_class.return_value = mock_client

    # Copy blank title joke to input directory
    source_joke = os.path.join(
      os.path.dirname(__file__),
      'fixtures',
      'jokes',
      'blank_title_joke.txt'
    )
    dest_joke = os.path.join(env['input_dir'], 'blank_title_joke.txt')
    shutil.copy(source_joke, dest_joke)

    # Run processor
    processor = CategorizedProcessor()
    processor.run()

    # Verify file moved to reject directory
    reject_file = os.path.join(env['reject_dir'], 'blank_title_joke.txt')
    assert os.path.exists(reject_file)

    # Verify rejection reason
    headers, content = parse_joke_file(reject_file)
    assert 'Rejection-Reason' in headers


def test_validation_short_content(setup_test_environment):
  """Test that validation fails with short content."""
  env = setup_test_environment

  # Create joke with short content
  headers = {
    'Joke-ID': '12345678-1234-1234-1234-123456789012',
    'Title': 'Short',
    'Submitter': 'test@example.com',
    'Source-Email-File': 'test.txt',
    'Pipeline-Stage': '06_categorized',
    'Cleanliness-Status': 'PASS',
    'Format-Status': 'PASS',
    'Categories': 'Puns'
  }
  content = 'Short'  # Only 5 characters

  dest_joke = os.path.join(env['input_dir'], 'short_joke.txt')
  write_joke_file(dest_joke, headers, content)

  # Run processor
  processor = CategorizedProcessor()
  processor.run()

  # Verify file moved to reject directory
  reject_file = os.path.join(env['reject_dir'], 'short_joke.txt')
  assert os.path.exists(reject_file)

  # Verify rejection reason
  headers, content = parse_joke_file(reject_file)
  assert 'Rejection-Reason' in headers
  assert 'content too short' in headers['Rejection-Reason'].lower()


def test_validation_cleanliness_fail(setup_test_environment):
  """Test that validation fails with Cleanliness-Status FAIL."""
  env = setup_test_environment

  # Create joke with Cleanliness-Status FAIL
  headers = {
    'Joke-ID': '12345678-1234-1234-1234-123456789012',
    'Title': 'Test',
    'Submitter': 'test@example.com',
    'Source-Email-File': 'test.txt',
    'Pipeline-Stage': '06_categorized',
    'Cleanliness-Status': 'FAIL',  # FAIL
    'Format-Status': 'PASS',
    'Categories': 'Puns'
  }
  content = 'This is a test joke with more than 10 characters.'

  dest_joke = os.path.join(env['input_dir'], 'unclean_joke.txt')
  write_joke_file(dest_joke, headers, content)

  # Run processor
  processor = CategorizedProcessor()
  processor.run()

  # Verify file moved to reject directory
  reject_file = os.path.join(env['reject_dir'], 'unclean_joke.txt')
  assert os.path.exists(reject_file)

  # Verify rejection reason
  headers, content = parse_joke_file(reject_file)
  assert 'Rejection-Reason' in headers
  assert 'cleanliness-status' in headers['Rejection-Reason'].lower()


def test_validation_format_fail(setup_test_environment):
  """Test that validation fails with Format-Status FAIL."""
  env = setup_test_environment

  # Create joke with Format-Status FAIL
  headers = {
    'Joke-ID': '12345678-1234-1234-1234-123456789012',
    'Title': 'Test',
    'Submitter': 'test@example.com',
    'Source-Email-File': 'test.txt',
    'Pipeline-Stage': '06_categorized',
    'Cleanliness-Status': 'PASS',
    'Format-Status': 'FAIL',  # FAIL
    'Categories': 'Puns'
  }
  content = 'This is a test joke with more than 10 characters.'

  dest_joke = os.path.join(env['input_dir'], 'unformatted_joke.txt')
  write_joke_file(dest_joke, headers, content)

  # Run processor
  processor = CategorizedProcessor()
  processor.run()

  # Verify file moved to reject directory
  reject_file = os.path.join(env['reject_dir'], 'unformatted_joke.txt')
  assert os.path.exists(reject_file)

  # Verify rejection reason
  headers, content = parse_joke_file(reject_file)
  assert 'Rejection-Reason' in headers
  assert 'format-status' in headers['Rejection-Reason'].lower()


def test_llm_error_handling(setup_test_environment):
  """Test handling of LLM errors during title generation."""
  env = setup_test_environment

  # Mock LLM to raise an exception
  with patch('stage_categorized.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.generate.side_effect = Exception('LLM connection error')
    mock_client_class.return_value = mock_client

    # Copy blank title joke to input directory
    source_joke = os.path.join(
      os.path.dirname(__file__),
      'fixtures',
      'jokes',
      'blank_title_joke.txt'
    )
    dest_joke = os.path.join(env['input_dir'], 'blank_title_joke.txt')
    shutil.copy(source_joke, dest_joke)

    # Run processor
    processor = CategorizedProcessor()
    processor.run()

    # Verify file moved to reject directory due to error
    reject_file = os.path.join(env['reject_dir'], 'blank_title_joke.txt')
    assert os.path.exists(reject_file)

    # Verify rejection reason
    headers, content = parse_joke_file(reject_file)
    assert 'Rejection-Reason' in headers
    assert 'llm error' in headers['Rejection-Reason'].lower()


def test_complete_flow_with_title_generation(
  setup_test_environment,
  mock_ollama_title_generation
):
  """Test complete flow: title generation + validation."""
  env = setup_test_environment

  # Copy blank title joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'blank_title_joke.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'blank_title_joke.txt')
  shutil.copy(source_joke, dest_joke)

  # Run processor
  processor = CategorizedProcessor()
  processor.run()

  # Verify file moved to ready_for_review
  output_file = os.path.join(env['output_dir'], 'blank_title_joke.txt')
  assert os.path.exists(output_file)

  # Verify all fields are correct
  headers, content = parse_joke_file(output_file)
  assert headers['Title'] == 'The Traveling Photon'
  assert headers['Pipeline-Stage'] == config.STAGES['ready_for_review']
  assert 'Joke-ID' in headers
  assert 'Categories' in headers
  assert headers['Cleanliness-Status'] == 'PASS'
  assert headers['Format-Status'] == 'PASS'
