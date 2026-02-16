#!/usr/bin/env python3
"""
Tests for stage_deduped.py - Cleanliness check using LLM.
"""

import os
import sys
import shutil
import tempfile
import pytest
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stage_deduped import DedupedProcessor
from file_utils import parse_joke_file
import config


@pytest.fixture
def setup_test_environment():
  """Setup and teardown for each test."""
  # Create temporary directories for testing
  test_dir = tempfile.mkdtemp(prefix="test_deduped_")
  pipeline_main = os.path.join(test_dir, "pipeline-main")
  pipeline_priority = os.path.join(test_dir, "pipeline-priority")

  # Create directory structure
  os.makedirs(os.path.join(pipeline_main, "03_deduped"))
  os.makedirs(os.path.join(pipeline_main, "04_clean_checked"))
  os.makedirs(os.path.join(pipeline_main, "52_rejected_cleanliness"))

  # Temporarily override config paths
  original_main = config.PIPELINE_MAIN
  original_priority = config.PIPELINE_PRIORITY
  config.PIPELINE_MAIN = pipeline_main
  config.PIPELINE_PRIORITY = pipeline_priority

  yield {
    'test_dir': test_dir,
    'pipeline_main': pipeline_main,
    'input_dir': os.path.join(pipeline_main, "03_deduped"),
    'output_dir': os.path.join(pipeline_main, "04_clean_checked"),
    'reject_dir': os.path.join(pipeline_main, "52_rejected_cleanliness")
  }

  # Cleanup
  config.PIPELINE_MAIN = original_main
  config.PIPELINE_PRIORITY = original_priority
  shutil.rmtree(test_dir)


@pytest.fixture
def mock_ollama_pass_high_confidence():
  """Mock Ollama client that returns PASS with high confidence."""
  with patch('stage_deduped.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.system_prompt = 'You are a content moderator.'
    mock_client.user_prompt_template = 'Evaluate: {content}'
    mock_client.generate.return_value = '{"status": "PASS", "confidence": 95, "reason": "This is a clean, family-friendly joke"}'
    mock_client.parse_structured_response.return_value = {
      'status': 'PASS',
      'confidence': '95',
      'reason': 'This is a clean, family-friendly joke'
    }
    mock_client.extract_confidence.return_value = 95
    mock_client_class.return_value = mock_client
    yield mock_client


@pytest.fixture
def mock_ollama_fail():
  """Mock Ollama client that returns FAIL."""
  with patch('stage_deduped.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.system_prompt = 'You are a content moderator.'
    mock_client.user_prompt_template = 'Evaluate: {content}'
    mock_client.generate.return_value = '{"status": "FAIL", "confidence": 85, "reason": "Contains inappropriate content"}'
    mock_client.parse_structured_response.return_value = {
      'status': 'FAIL',
      'confidence': '85',
      'reason': 'Contains inappropriate content'
    }
    mock_client.extract_confidence.return_value = 85
    mock_client_class.return_value = mock_client
    yield mock_client


@pytest.fixture
def mock_ollama_low_confidence():
  """Mock Ollama client that returns PASS with low confidence."""
  with patch('stage_deduped.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.system_prompt = 'You are a content moderator.'
    mock_client.user_prompt_template = 'Evaluate: {content}'
    mock_client.generate.return_value = '{"status": "PASS", "confidence": 50, "reason": "Uncertain about appropriateness"}'
    mock_client.parse_structured_response.return_value = {
      'status': 'PASS',
      'confidence': '50',
      'reason': 'Uncertain about appropriateness'
    }
    mock_client.extract_confidence.return_value = 50
    mock_client_class.return_value = mock_client
    yield mock_client


def test_clean_joke_passes(
  setup_test_environment,
  mock_ollama_pass_high_confidence
):
  """Test that a clean joke passes cleanliness check."""
  env = setup_test_environment

  # Copy clean joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'clean_joke.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'clean_joke.txt')
  shutil.copy(source_joke, dest_joke)

  # Run processor
  processor = DedupedProcessor()
  processor.run()

  # Verify file moved to output directory
  output_file = os.path.join(env['output_dir'], 'clean_joke.txt')
  assert os.path.exists(output_file)
  assert not os.path.exists(dest_joke)

  # Verify metadata
  headers, content = parse_joke_file(output_file)
  assert headers['Cleanliness-Status'] == 'PASS'
  assert headers['Cleanliness-Confidence'] == '95'
  assert headers['Pipeline-Stage'] == config.STAGES['clean_checked']


def test_questionable_joke_fails(
  setup_test_environment,
  mock_ollama_fail
):
  """Test that a questionable joke fails cleanliness check."""
  env = setup_test_environment

  # Copy questionable joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'questionable_joke.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'questionable_joke.txt')
  shutil.copy(source_joke, dest_joke)

  # Run processor
  processor = DedupedProcessor()
  processor.run()

  # Verify file moved to reject directory
  reject_file = os.path.join(env['reject_dir'], 'questionable_joke.txt')
  assert os.path.exists(reject_file)
  assert not os.path.exists(dest_joke)

  # Verify metadata
  headers, content = parse_joke_file(reject_file)
  assert headers['Cleanliness-Status'] == 'FAIL'
  assert headers['Cleanliness-Confidence'] == '85'
  assert headers['Pipeline-Stage'] == config.REJECTS['cleanliness']
  assert 'Rejection-Reason' in headers
  assert 'inappropriate content' in headers['Rejection-Reason'].lower()


def test_low_confidence_rejected(
  setup_test_environment,
  mock_ollama_low_confidence
):
  """Test that low confidence results in rejection even if status is PASS."""
  env = setup_test_environment

  # Copy clean joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'clean_joke.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'clean_joke.txt')
  shutil.copy(source_joke, dest_joke)

  # Run processor
  processor = DedupedProcessor()
  processor.run()

  # Verify file moved to reject directory
  reject_file = os.path.join(env['reject_dir'], 'clean_joke.txt')
  assert os.path.exists(reject_file)
  assert not os.path.exists(dest_joke)

  # Verify metadata
  headers, content = parse_joke_file(reject_file)
  assert headers['Cleanliness-Status'] == 'PASS'
  assert headers['Cleanliness-Confidence'] == '50'
  assert 'Rejection-Reason' in headers
  assert 'confidence' in headers['Rejection-Reason'].lower()
  assert '50' in headers['Rejection-Reason']


def test_metadata_updates(
  setup_test_environment,
  mock_ollama_pass_high_confidence
):
  """Test that metadata fields are updated correctly."""
  env = setup_test_environment

  # Copy clean joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'clean_joke.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'clean_joke.txt')
  shutil.copy(source_joke, dest_joke)

  # Run processor
  processor = DedupedProcessor()
  processor.run()

  # Verify metadata
  output_file = os.path.join(env['output_dir'], 'clean_joke.txt')
  headers, content = parse_joke_file(output_file)

  # Check required fields
  assert 'Cleanliness-Status' in headers
  assert 'Cleanliness-Confidence' in headers
  assert headers['Cleanliness-Status'] in ['PASS', 'FAIL']

  # Confidence should be an integer string
  confidence = int(headers['Cleanliness-Confidence'])
  assert 0 <= confidence <= 100


def test_llm_error_handling(setup_test_environment):
  """Test handling of LLM errors."""
  env = setup_test_environment

  # Mock LLM to raise an exception
  with patch('stage_deduped.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.generate.side_effect = Exception('LLM connection error')
    mock_client_class.return_value = mock_client

    # Copy clean joke to input directory
    source_joke = os.path.join(
      os.path.dirname(__file__),
      'fixtures',
      'jokes',
      'clean_joke.txt'
    )
    dest_joke = os.path.join(env['input_dir'], 'clean_joke.txt')
    shutil.copy(source_joke, dest_joke)

    # Run processor
    processor = DedupedProcessor()
    processor.run()

    # Verify file moved to reject directory due to error
    reject_file = os.path.join(env['reject_dir'], 'clean_joke.txt')
    assert os.path.exists(reject_file)

    # Verify rejection reason
    headers, content = parse_joke_file(reject_file)
    assert 'Rejection-Reason' in headers
    assert 'LLM error' in headers['Rejection-Reason']


def test_multiple_jokes(
  setup_test_environment,
  mock_ollama_pass_high_confidence
):
  """Test processing multiple jokes."""
  env = setup_test_environment

  # Copy multiple jokes to input directory
  source_joke1 = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'clean_joke.txt'
  )
  source_joke2 = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'questionable_joke.txt'
  )

  dest_joke1 = os.path.join(env['input_dir'], 'joke1.txt')
  dest_joke2 = os.path.join(env['input_dir'], 'joke2.txt')

  shutil.copy(source_joke1, dest_joke1)
  shutil.copy(source_joke2, dest_joke2)

  # Run processor
  processor = DedupedProcessor()
  processor.run()

  # Verify both files processed
  output_file1 = os.path.join(env['output_dir'], 'joke1.txt')
  output_file2 = os.path.join(env['output_dir'], 'joke2.txt')

  assert os.path.exists(output_file1)
  assert os.path.exists(output_file2)
