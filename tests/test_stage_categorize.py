#!/usr/bin/env python3
"""
Tests for stage_categorize.py - Categorization using LLM.
"""

import os
import sys
import shutil
import tempfile
import pytest
import json
import numpy as np
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stage_categorize import CategorizeProcessor
from file_utils import parse_joke_file
import config
import joke_categories


@pytest.fixture
def setup_test_environment():
  """Setup and teardown for each test."""
  # Create temporary directories for testing
  test_dir = tempfile.mkdtemp(prefix="test_categorize_")
  pipeline_main = os.path.join(test_dir, "pipeline-main")
  pipeline_priority = os.path.join(test_dir, "pipeline-priority")

  # Create directory structure
  os.makedirs(os.path.join(pipeline_main, "05_categorize"))
  os.makedirs(os.path.join(pipeline_main, "06_title"))
  os.makedirs(os.path.join(pipeline_main, "54_rejected_categorize"))

  # Temporarily override config paths
  original_main = config.PIPELINE_MAIN
  original_priority = config.PIPELINE_PRIORITY
  config.PIPELINE_MAIN = pipeline_main
  config.PIPELINE_PRIORITY = pipeline_priority

  yield {
    'test_dir': test_dir,
    'pipeline_main': pipeline_main,
    'input_dir': os.path.join(pipeline_main, "05_categorize"),
    'output_dir': os.path.join(pipeline_main, "06_title"),
    'reject_dir': os.path.join(pipeline_main, "54_rejected_categorize")
  }

  # Cleanup
  config.PIPELINE_MAIN = original_main
  config.PIPELINE_PRIORITY = original_priority
  shutil.rmtree(test_dir)


@pytest.fixture
def mock_ollama_one_category():
  """Mock Ollama client that returns 1 category."""
  with patch('stage_categorize.OllamaClient') as mock_client_class:
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
  with patch('stage_categorize.OllamaClient') as mock_client_class:
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
  with patch('stage_categorize.OllamaClient') as mock_client_class:
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
  with patch('stage_categorize.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.system_prompt = 'You are a joke categorizer.'
    mock_client.user_prompt_template = 'Categorize: {content}'
    import json as json_lib
    mock_client.generate.return_value = json_lib.dumps({"categories": ["ZZZZZ_INVALID"], "reason": "This is not a valid category"})
    mock_client.parse_structured_response.return_value = {
      'categories': ['ZZZZZ_INVALID'],
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
  with patch('stage_categorize.OllamaClient') as mock_client_class:
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
  processor = CategorizeProcessor()
  processor.run()

  # Verify file moved to output directory
  output_file = os.path.join(env['output_dir'], 'pun_joke.txt')
  assert os.path.exists(output_file)
  assert not os.path.exists(dest_joke)

  # Verify metadata
  headers, content = parse_joke_file(output_file)
  assert headers['Categories'] == 'Pun'
  assert 'Category-Confidence' not in headers
  assert headers['Pipeline-Stage'] == config.STAGES['title']


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
  processor = CategorizeProcessor()
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
  processor = CategorizeProcessor()
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
  processor = CategorizeProcessor()
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
  processor = CategorizeProcessor()
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

  with patch('stage_categorize.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client.system_prompt = 'You are a joke categorizer.'
    mock_client.user_prompt_template = 'Categorize: {content}'
    # Animals and Food are valid; ZZZZFAKE and QQQNOREAL are unmatchable
    mock_client.generate.return_value = json.dumps({
      "categories": ["Animals", "ZZZZFAKE", "Food", "QQQNOREAL"],
      "reason": "Mix of valid and invalid"
    })
    mock_client.parse_structured_response.return_value = {
      'categories': ['Animals', 'ZZZZFAKE', 'Food', 'QQQNOREAL'],
      'reason': 'Mix of valid and invalid'
    }
    mock_client_class.return_value = mock_client

    source_joke = os.path.join(
      os.path.dirname(__file__), 'fixtures', 'jokes', 'animal_pun.txt'
    )
    shutil.copy(source_joke, os.path.join(env['input_dir'], 'animal_pun.txt'))

    processor = CategorizeProcessor()
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

  with patch('stage_categorize.OllamaClient') as mock_client_class:
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

    processor = CategorizeProcessor()
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

  with patch('stage_categorize.OllamaClient') as mock_client_class:
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

    processor = CategorizeProcessor()
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
  processor = CategorizeProcessor()
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
  assert 'Categorize-Reason' in headers
  assert 'Categorize-LLM-Model-Used' in headers


def test_case_insensitive_category_matching(setup_test_environment):
  """Test that category validation is case-insensitive."""
  env = setup_test_environment

  # Mock LLM to return lowercase category
  with patch('stage_categorize.OllamaClient') as mock_client_class:
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
    processor = CategorizeProcessor()
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
  with patch('stage_categorize.OllamaClient') as mock_client_class:
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
    processor = CategorizeProcessor()
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
  with patch('stage_categorize.OllamaClient') as mock_client_class:
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
    processor = CategorizeProcessor()
    processor.run()

    # Verify file moved to reject directory
    reject_file = os.path.join(env['reject_dir'], 'pun_joke.txt')
    assert os.path.exists(reject_file)

    # Verify rejection reason
    headers, content = parse_joke_file(reject_file)
    assert 'Rejection-Reason' in headers


# ---------------------------------------------------------------------------
# Embedding pre-filter tests
# ---------------------------------------------------------------------------

def _make_fake_embeddings(n: int, dim: int = 8) -> list:
  """Return n fake embedding vectors (lists of floats) of the given dimension."""
  rng = np.random.default_rng(42)
  return rng.standard_normal((n, dim)).tolist()


def test_prefilter_embeddings_computed_on_init():
  """__init__ pre-computes _category_embeddings as a numpy array when embed succeeds."""
  n_cats = len(joke_categories.VALID_CATEGORIES)
  dim = 8
  fake_embeddings = _make_fake_embeddings(n_cats, dim)

  with patch('stage_categorize.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    mock_client_class.embed.return_value = fake_embeddings

    processor = CategorizeProcessor()

  assert processor._category_embeddings is not None
  assert isinstance(processor._category_embeddings, np.ndarray)
  assert processor._category_embeddings.shape == (n_cats, dim)


def test_prefilter_embeddings_none_when_embed_raises():
  """__init__ sets _category_embeddings to None when the embed call fails."""
  with patch('stage_categorize.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    mock_client_class.embed.side_effect = Exception("connection refused")

    processor = CategorizeProcessor()

  assert processor._category_embeddings is None


def test_prefilter_categories_returns_top_n():
  """_prefilter_categories returns at most prefilter_top_n items."""
  n_cats = len(joke_categories.VALID_CATEGORIES)
  dim = 16
  fake_cat_embeddings = _make_fake_embeddings(n_cats, dim)
  fake_joke_embedding = _make_fake_embeddings(1, dim)

  with patch('stage_categorize.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    # First embed call (init) returns category embeddings
    mock_client_class.embed.side_effect = [
      fake_cat_embeddings,
      fake_joke_embedding,
    ]

    processor = CategorizeProcessor()
    result = processor._prefilter_categories("Why did the doctor laugh?", "test-id")

  assert len(result) == processor.prefilter_top_n


def test_prefilter_categories_all_from_valid_categories():
  """All items returned by _prefilter_categories are members of VALID_CATEGORIES."""
  n_cats = len(joke_categories.VALID_CATEGORIES)
  dim = 16
  fake_cat_embeddings = _make_fake_embeddings(n_cats, dim)
  fake_joke_embedding = _make_fake_embeddings(1, dim)

  with patch('stage_categorize.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    mock_client_class.embed.side_effect = [
      fake_cat_embeddings,
      fake_joke_embedding,
    ]

    processor = CategorizeProcessor()
    result = processor._prefilter_categories("Some joke text here.", "test-id")

  for cat in result:
    assert cat in joke_categories.VALID_CATEGORIES


def test_prefilter_categories_fallback_on_embed_exception():
  """_prefilter_categories falls back to the full list when embed raises during per-joke call."""
  n_cats = len(joke_categories.VALID_CATEGORIES)
  dim = 8
  fake_cat_embeddings = _make_fake_embeddings(n_cats, dim)

  with patch('stage_categorize.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    # Init succeeds, per-joke embed fails
    mock_client_class.embed.side_effect = [
      fake_cat_embeddings,
      Exception("timeout"),
    ]

    processor = CategorizeProcessor()
    result = processor._prefilter_categories("Some joke.", "test-id")

  assert result == joke_categories.VALID_CATEGORIES


def test_prefilter_categories_fallback_when_embeddings_none():
  """_prefilter_categories returns the full list when _category_embeddings is None."""
  with patch('stage_categorize.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    mock_client_class.embed.side_effect = Exception("server down")

    processor = CategorizeProcessor()
    assert processor._category_embeddings is None
    result = processor._prefilter_categories("Any joke.", "test-id")

  assert result == joke_categories.VALID_CATEGORIES


def test_process_file_uses_prefiltered_categories(setup_test_environment):
  """process_file passes the pre-filtered (smaller) category list to the LLM prompt."""
  env = setup_test_environment
  n_cats = len(joke_categories.VALID_CATEGORIES)
  dim = 8
  fake_cat_embeddings = _make_fake_embeddings(n_cats, dim)
  fake_joke_embedding = _make_fake_embeddings(1, dim)

  with patch('stage_categorize.OllamaClient') as mock_client_class:
    mock_client = Mock()
    mock_client_class.return_value = mock_client
    # Capture the prompt to inspect later
    captured_prompts = []

    def fake_generate(system_prompt, user_prompt, timeout=None):
      captured_prompts.append(user_prompt)
      return json.dumps({"categories": ["Pun"], "reason": "wordplay"})

    mock_client.generate.side_effect = fake_generate
    mock_client.system_prompt = 'You are a categorizer.'
    mock_client.user_prompt_template = '{categories_list}|{content}'

    # Init: embed returns category embeddings; per-joke: returns joke embedding
    mock_client_class.embed.side_effect = [
      fake_cat_embeddings,
      fake_joke_embedding,
    ]

    source_joke = os.path.join(
      os.path.dirname(__file__), 'fixtures', 'jokes', 'pun_joke.txt'
    )
    shutil.copy(source_joke, os.path.join(env['input_dir'], 'pun_joke.txt'))

    processor = CategorizeProcessor()
    processor.run()

  # The prompt should have been captured
  assert len(captured_prompts) == 1
  categories_part = captured_prompts[0].split('|')[0]
  sent_categories = [c for c in categories_part.split(',') if c]
  # Should have sent a subset, not the full list
  assert len(sent_categories) == processor.prefilter_top_n
  assert len(sent_categories) < n_cats
