#!/usr/bin/env python3
"""
Tests for stage_formatted.py - Categorization using LLM.
"""

import os
import sys
import shutil
import tempfile
import pytest
import json
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stage_formatted import FormattedProcessor
from file_utils import parse_joke_file
import config
import joke_categories


@pytest.fixture
def setup_test_environment():
  """Setup and teardown for each test."""
  # Create temporary directories for testing
  test_dir = tempfile.mkdtemp(prefix="test_formatted_")
  pipeline_main = os.path.join(test_dir, "pipeline-main")
  pipeline_priority = os.path.join(test_dir, "pipeline-priority")

  # Create directory structure
  os.makedirs(os.path.join(pipeline_main, "05_formatted"))
  os.makedirs(os.path.join(pipeline_main, "06_categorized"))
  os.makedirs(os.path.join(pipeline_main, "54_rejected_category"))

  # Temporarily override config paths
  original_main = config.PIPELINE_MAIN
  original_priority = config.PIPELINE_PRIORITY
  config.PIPELINE_MAIN = pipeline_main
  config.PIPELINE_PRIORITY = pipeline_priority

  yield {
    'test_dir': test_dir,
    'pipeline_main': pipeline_main,
    'input_dir': os.path.join(pipeline_main, "05_formatted"),
    'output_dir': os.path.join(pipeline_main, "06_categorized"),
    'reject_dir': os.path.join(pipeline_main, "54_rejected_category")
  }

  # Cleanup
  config.PIPELINE_MAIN = original_main
  config.PIPELINE_PRIORITY = original_priority
  shutil.rmtree(test_dir)


@pytest.fixture
def mock_ollama_one_category():
  """Mock Ollama client that returns 1 category."""
  with patch('stage_formatted.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.system_prompt = 'You are a joke categorizer.'
    mock_client.user_prompt_template = 'Categorize: {content}'
    mock_client.generate.return_value = json.dumps({"categories": ["Pun"], "confidence": 85, "reason": "This joke uses wordplay with financial terms"})
    mock_client.parse_structured_response.return_value = {
      'categories': ['Pun'],
      'confidence': '85',
      'reason': 'This joke uses wordplay with financial terms'
    }
    mock_client.extract_confidence.return_value = 85
    mock_client_class.return_value = mock_client
    yield mock_client


@pytest.fixture
def mock_ollama_two_categories():
  """Mock Ollama client that returns 2 categories."""
  with patch('stage_formatted.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.system_prompt = 'You are a joke categorizer.'
    mock_client.user_prompt_template = 'Categorize: {content}'
    mock_client.generate.return_value = json.dumps({"categories": ["Animals", "Pun"], "confidence": 90, "reason": "Combines animal subject with wordplay"})
    mock_client.parse_structured_response.return_value = {
      'categories': ['Animals', 'Pun'],
      'confidence': '90',
      'reason': 'Combines animal subject with wordplay'
    }
    mock_client.extract_confidence.return_value = 90
    mock_client_class.return_value = mock_client
    yield mock_client


@pytest.fixture
def mock_ollama_three_categories():
  """Mock Ollama client that returns 3 categories."""
  with patch('stage_formatted.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.system_prompt = 'You are a joke categorizer.'
    mock_client.user_prompt_template = 'Categorize: {content}'
    mock_client.generate.return_value = json.dumps({"categories": ["Animals", "Pun", "Food"], "confidence": 88, "reason": "Contains animal theme, wordplay, and food reference"})
    mock_client.parse_structured_response.return_value = {
      'categories': ['Animals', 'Pun', 'Food'],
      'confidence': '88',
      'reason': 'Contains animal theme, wordplay, and food reference'
    }
    mock_client.extract_confidence.return_value = 88
    mock_client_class.return_value = mock_client
    yield mock_client


@pytest.fixture
def mock_ollama_invalid_category():
  """Mock Ollama client that returns invalid category."""
  with patch('stage_formatted.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.system_prompt = 'You are a joke categorizer.'
    mock_client.user_prompt_template = 'Categorize: {content}'
    import json as json_lib
    mock_client.generate.return_value = json_lib.dumps({"categories": ["InvalidCategory"], "confidence": 85, "reason": "This is not a valid category"})
    mock_client.parse_structured_response.return_value = {
      'categories': ['InvalidCategory'],
      'confidence': '85',
      'reason': 'This is not a valid category'
    }
    mock_client.extract_confidence.return_value = 85
    mock_client_class.return_value = mock_client
    yield mock_client


@pytest.fixture
def mock_ollama_too_many_categories():
  """Mock Ollama client that returns too many categories (11 > max of 10)."""
  too_many = [
    "Animals", "Pun", "Food", "Technology", "Sports",
    "Music", "Movie", "Science", "Travel", "History", "Weather"
  ]
  with patch('stage_formatted.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.system_prompt = 'You are a joke categorizer.'
    mock_client.user_prompt_template = 'Categorize: {content}'
    import json as json_lib
    mock_client.generate.return_value = json_lib.dumps({"categories": too_many, "confidence": 85, "reason": "Too many categories assigned"})  # noqa: E501
    mock_client.parse_structured_response.return_value = {
      'categories': too_many,
      'confidence': '85',
      'reason': 'Too many categories assigned'
    }
    mock_client.extract_confidence.return_value = 85
    mock_client_class.return_value = mock_client
    yield mock_client



def test_one_category(setup_test_environment, mock_ollama_one_category):
  """Test categorization with 1 category."""
  env = setup_test_environment

  # Copy pun joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'pun_joke.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'pun_joke.txt')
  shutil.copy(source_joke, dest_joke)

  # Run processor
  processor = FormattedProcessor()
  processor.run()

  # Verify file moved to output directory
  output_file = os.path.join(env['output_dir'], 'pun_joke.txt')
  assert os.path.exists(output_file)
  assert not os.path.exists(dest_joke)

  # Verify metadata
  headers, content = parse_joke_file(output_file)
  assert headers['Categories'] == 'Pun'
  assert 'Category-Confidence' not in headers
  assert headers['Pipeline-Stage'] == config.STAGES['categorized']


def test_two_categories(setup_test_environment, mock_ollama_two_categories):
  """Test categorization with 2 categories."""
  env = setup_test_environment

  # Copy animal pun joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'animal_pun.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'animal_pun.txt')
  shutil.copy(source_joke, dest_joke)

  # Run processor
  processor = FormattedProcessor()
  processor.run()

  # Verify file moved to output directory
  output_file = os.path.join(env['output_dir'], 'animal_pun.txt')
  assert os.path.exists(output_file)

  # Verify metadata
  headers, content = parse_joke_file(output_file)
  assert headers['Categories'] == 'Animals, Pun'
  assert 'Category-Confidence' not in headers


def test_three_categories(setup_test_environment, mock_ollama_three_categories):
  """Test categorization with 3 categories."""
  env = setup_test_environment

  # Copy animal pun joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'animal_pun.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'animal_pun.txt')
  shutil.copy(source_joke, dest_joke)

  # Run processor
  processor = FormattedProcessor()
  processor.run()

  # Verify file moved to output directory
  output_file = os.path.join(env['output_dir'], 'animal_pun.txt')
  assert os.path.exists(output_file)

  # Verify metadata
  headers, content = parse_joke_file(output_file)
  assert headers['Categories'] == 'Animals, Pun, Food'
  assert 'Category-Confidence' not in headers


def test_all_invalid_categories_rejected(
  setup_test_environment,
  mock_ollama_invalid_category
):
  """Test that all-invalid categories (none in VALID_CATEGORIES) results in rejection."""
  env = setup_test_environment

  # Copy joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'pun_joke.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'pun_joke.txt')
  shutil.copy(source_joke, dest_joke)

  # Run processor
  processor = FormattedProcessor()
  processor.run()

  # Verify file moved to reject directory
  reject_file = os.path.join(env['reject_dir'], 'pun_joke.txt')
  assert os.path.exists(reject_file)
  assert not os.path.exists(dest_joke)

  # Verify rejection reason says no valid categories remain
  headers, content = parse_joke_file(reject_file)
  assert 'Rejection-Reason' in headers
  assert 'no valid categories' in headers['Rejection-Reason'].lower()


def test_too_many_valid_categories_truncated(
  setup_test_environment,
  mock_ollama_too_many_categories
):
  """Test that more than MAX valid categories are silently truncated to MAX."""
  env = setup_test_environment

  # Copy joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'animal_pun.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'animal_pun.txt')
  shutil.copy(source_joke, dest_joke)

  # Run processor
  processor = FormattedProcessor()
  processor.run()

  # Verify file moved to OUTPUT (not reject) directory
  output_file = os.path.join(env['output_dir'], 'animal_pun.txt')
  assert os.path.exists(output_file)
  assert not os.path.exists(dest_joke)

  # Verify exactly MAX_CATEGORIES_PER_JOKE categories were kept
  headers, content = parse_joke_file(output_file)
  categories = [cat.strip() for cat in headers['Categories'].split(',')]
  assert len(categories) == joke_categories.MAX_CATEGORIES_PER_JOKE
  # First 10 of the 11 provided should be kept (Weather is the 11th, dropped)
  expected = [
    "Animals", "Pun", "Food", "Technology", "Sports",
    "Music", "Movie", "Science", "Travel", "History"
  ]
  assert categories == expected


def test_some_invalid_categories_filtered(setup_test_environment):
  """Test that invalid categories are filtered out when count is within max."""
  env = setup_test_environment

  with patch('stage_formatted.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.system_prompt = 'You are a joke categorizer.'
    mock_client.user_prompt_template = 'Categorize: {content}'
    # Animals and Food are valid; FakeCategory and NotReal are not
    mock_client.generate.return_value = json.dumps({
      "categories": ["Animals", "FakeCategory", "Food", "NotReal"],
      "confidence": 85,
      "reason": "Mix of valid and invalid"
    })
    mock_client.parse_structured_response.return_value = {
      'categories': ['Animals', 'FakeCategory', 'Food', 'NotReal'],
      'confidence': '85',
      'reason': 'Mix of valid and invalid'
    }
    mock_client.extract_confidence.return_value = 85
    mock_client_class.return_value = mock_client

    source_joke = os.path.join(
      os.path.dirname(__file__), 'fixtures', 'jokes', 'animal_pun.txt'
    )
    shutil.copy(source_joke, os.path.join(env['input_dir'], 'animal_pun.txt'))

    processor = FormattedProcessor()
    processor.run()

    # File should succeed — valid categories were kept
    output_file = os.path.join(env['output_dir'], 'animal_pun.txt')
    assert os.path.exists(output_file)

    headers, content = parse_joke_file(output_file)
    categories = [cat.strip() for cat in headers['Categories'].split(',')]
    assert categories == ['Animals', 'Food']


def test_invalid_and_over_max_categories(setup_test_environment):
  """Test filtering invalids then truncating: 12 cats (4 invalid) → keep first 8 valid."""
  env = setup_test_environment

  with patch('stage_formatted.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.system_prompt = 'You are a joke categorizer.'
    mock_client.user_prompt_template = 'Categorize: {content}'
    # 12 categories: 4 invalid interspersed. After filtering: 8 valid (within max=10).
    mock_client.generate.return_value = json.dumps({
      "categories": [
        "Animals", "FakeOne", "Pun", "Food", "FakeTwo",
        "Technology", "Sports", "FakeThree", "Music", "Movie",
        "Science", "FakeFour"
      ],
      "confidence": 80,
      "reason": "Mixed valid and invalid over max"
    })
    mock_client.parse_structured_response.return_value = {
      'categories': [
        "Animals", "FakeOne", "Pun", "Food", "FakeTwo",
        "Technology", "Sports", "FakeThree", "Music", "Movie",
        "Science", "FakeFour"
      ],
      'confidence': '80',
      'reason': 'Mixed valid and invalid over max'
    }
    mock_client.extract_confidence.return_value = 80
    mock_client_class.return_value = mock_client

    source_joke = os.path.join(
      os.path.dirname(__file__), 'fixtures', 'jokes', 'animal_pun.txt'
    )
    shutil.copy(source_joke, os.path.join(env['input_dir'], 'animal_pun.txt'))

    processor = FormattedProcessor()
    processor.run()

    # Should succeed — 8 valid categories is within MAX_CATEGORIES_PER_JOKE
    output_file = os.path.join(env['output_dir'], 'animal_pun.txt')
    assert os.path.exists(output_file)

    headers, content = parse_joke_file(output_file)
    categories = [cat.strip() for cat in headers['Categories'].split(',')]
    assert categories == [
      "Animals", "Pun", "Food", "Technology", "Sports",
      "Music", "Movie", "Science"
    ]


def test_invalid_and_over_max_truncated(setup_test_environment):
  """Test filtering invalids then truncating when valid count still exceeds max."""
  env = setup_test_environment

  with patch('stage_formatted.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.system_prompt = 'You are a joke categorizer.'
    mock_client.user_prompt_template = 'Categorize: {content}'
    # 13 categories: 1 invalid + 12 valid → filter to 12 valid → truncate to 10
    mock_client.generate.return_value = json.dumps({
      "categories": [
        "Animals", "FakeOne", "Pun", "Food", "Technology", "Sports",
        "Music", "Movie", "Science", "Travel", "History", "Weather", "Age"
      ],
      "confidence": 80,
      "reason": "One invalid then 12 valid"
    })
    mock_client.parse_structured_response.return_value = {
      'categories': [
        "Animals", "FakeOne", "Pun", "Food", "Technology", "Sports",
        "Music", "Movie", "Science", "Travel", "History", "Weather", "Age"
      ],
      'confidence': '80',
      'reason': 'One invalid then 12 valid'
    }
    mock_client.extract_confidence.return_value = 80
    mock_client_class.return_value = mock_client

    source_joke = os.path.join(
      os.path.dirname(__file__), 'fixtures', 'jokes', 'animal_pun.txt'
    )
    shutil.copy(source_joke, os.path.join(env['input_dir'], 'animal_pun.txt'))

    processor = FormattedProcessor()
    processor.run()

    # Should succeed with exactly MAX categories
    output_file = os.path.join(env['output_dir'], 'animal_pun.txt')
    assert os.path.exists(output_file)

    headers, content = parse_joke_file(output_file)
    categories = [cat.strip() for cat in headers['Categories'].split(',')]
    assert len(categories) == joke_categories.MAX_CATEGORIES_PER_JOKE
    # FakeOne filtered, then first 10 of remaining 12 kept
    assert categories == [
      "Animals", "Pun", "Food", "Technology", "Sports",
      "Music", "Movie", "Science", "Travel", "History"
    ]


def test_metadata_updates(setup_test_environment, mock_ollama_one_category):
  """Test that metadata fields are updated correctly."""
  env = setup_test_environment

  # Copy joke to input directory
  source_joke = os.path.join(
    os.path.dirname(__file__),
    'fixtures',
    'jokes',
    'pun_joke.txt'
  )
  dest_joke = os.path.join(env['input_dir'], 'pun_joke.txt')
  shutil.copy(source_joke, dest_joke)

  # Run processor
  processor = FormattedProcessor()
  processor.run()

  # Verify metadata
  output_file = os.path.join(env['output_dir'], 'pun_joke.txt')
  headers, content = parse_joke_file(output_file)

  # Check required fields
  assert 'Categories' in headers
  assert 'Category-Confidence' not in headers

  # Categories should be from valid list
  categories = [cat.strip() for cat in headers['Categories'].split(',')]
  for cat in categories:
    assert cat in joke_categories.VALID_CATEGORIES


def test_case_insensitive_category_matching(setup_test_environment):
  """Test that category validation is case-insensitive."""
  env = setup_test_environment

  # Mock LLM to return lowercase category
  with patch('stage_formatted.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.system_prompt = 'You are a joke categorizer.'
    mock_client.user_prompt_template = 'Categorize: {content}'
    mock_client.generate.return_value = json.dumps({"categories": ["pun"], "confidence": 85, "reason": "Testing case insensitivity"})
    mock_client.parse_structured_response.return_value = {
      'categories': ['pun'],
      'confidence': '85',
      'reason': 'Testing case insensitivity'
    }
    mock_client.extract_confidence.return_value = 85
    mock_client_class.return_value = mock_client

    # Copy joke to input directory
    source_joke = os.path.join(
      os.path.dirname(__file__),
      'fixtures',
      'jokes',
      'pun_joke.txt'
    )
    dest_joke = os.path.join(env['input_dir'], 'pun_joke.txt')
    shutil.copy(source_joke, dest_joke)

    # Run processor
    processor = FormattedProcessor()
    processor.run()

    # Verify file moved to output directory
    output_file = os.path.join(env['output_dir'], 'pun_joke.txt')
    assert os.path.exists(output_file)

    # Verify category was normalized to canonical form
    headers, content = parse_joke_file(output_file)
    assert headers['Categories'] == 'Pun'  # Canonical capitalization


def test_llm_error_handling(setup_test_environment):
  """Test handling of LLM errors."""
  env = setup_test_environment

  # Mock LLM to raise an exception
  with patch('stage_formatted.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.generate.side_effect = Exception('LLM connection error')
    mock_client_class.return_value = mock_client

    # Copy joke to input directory
    source_joke = os.path.join(
      os.path.dirname(__file__),
      'fixtures',
      'jokes',
      'pun_joke.txt'
    )
    dest_joke = os.path.join(env['input_dir'], 'pun_joke.txt')
    shutil.copy(source_joke, dest_joke)

    # Run processor
    processor = FormattedProcessor()
    processor.run()

    # Verify file moved to reject directory due to error
    reject_file = os.path.join(env['reject_dir'], 'pun_joke.txt')
    assert os.path.exists(reject_file)

    # Verify rejection reason
    headers, content = parse_joke_file(reject_file)
    assert 'Rejection-Reason' in headers
    assert 'LLM error' in headers['Rejection-Reason']


def test_no_categories_rejected(setup_test_environment):
  """Test that no categories results in rejection."""
  env = setup_test_environment

  # Mock LLM to return empty categories
  with patch('stage_formatted.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.generate.return_value = """
Categories:
Confidence: 85
Reasoning: Could not categorize
"""
    mock_client.parse_structured_response.return_value = {
      'Categories': '',
      'Confidence': '85',
      'Reasoning': 'Could not categorize'
    }
    mock_client.extract_confidence.return_value = 85
    mock_client_class.return_value = mock_client

    # Copy joke to input directory
    source_joke = os.path.join(
      os.path.dirname(__file__),
      'fixtures',
      'jokes',
      'pun_joke.txt'
    )
    dest_joke = os.path.join(env['input_dir'], 'pun_joke.txt')
    shutil.copy(source_joke, dest_joke)

    # Run processor
    processor = FormattedProcessor()
    processor.run()

    # Verify file moved to reject directory
    reject_file = os.path.join(env['reject_dir'], 'pun_joke.txt')
    assert os.path.exists(reject_file)

    # Verify rejection reason
    headers, content = parse_joke_file(reject_file)
    assert 'Rejection-Reason' in headers
