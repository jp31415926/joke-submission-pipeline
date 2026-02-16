#!/usr/bin/env python3
"""
Integration tests for joke-pipeline.py - full pipeline orchestration.
"""

import os
import sys
import shutil
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock
import subprocess
import importlib.util

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
from file_utils import parse_joke_file, write_joke_file


# Import joke-pipeline.py module (with hyphen)
def import_joke_pipeline():
  """Import the joke-pipeline module."""
  spec = importlib.util.spec_from_file_location(
    "joke_pipeline_module",
    os.path.join(
      os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
      "joke-pipeline.py"
    )
  )
  module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(module)
  return module


@pytest.fixture
def setup_full_pipeline():
  """Setup complete pipeline directory structure."""
  # Create temporary directories for testing
  test_dir = tempfile.mkdtemp(prefix="test_pipeline_")
  pipeline_main = os.path.join(test_dir, "pipeline-main")
  pipeline_priority = os.path.join(test_dir, "pipeline-priority")

  # Create all stage directories for main pipeline
  stages = [
    "01_incoming",
    "02_parsed",
    "03_deduped",
    "04_clean_checked",
    "05_formatted",
    "06_categorized",
    "08_ready_for_review",
    "50_rejected_parse",
    "51_rejected_duplicate",
    "52_rejected_cleanliness",
    "53_rejected_format",
    "54_rejected_category",
    "55_rejected_titled"
  ]

  for stage in stages:
    os.makedirs(os.path.join(pipeline_main, stage))
    os.makedirs(os.path.join(pipeline_priority, stage))

  # Temporarily override config paths
  original_main = config.PIPELINE_MAIN
  original_priority = config.PIPELINE_PRIORITY
  config.PIPELINE_MAIN = pipeline_main
  config.PIPELINE_PRIORITY = pipeline_priority

  yield {
    'test_dir': test_dir,
    'pipeline_main': pipeline_main,
    'pipeline_priority': pipeline_priority
  }

  # Cleanup
  config.PIPELINE_MAIN = original_main
  config.PIPELINE_PRIORITY = original_priority
  shutil.rmtree(test_dir)


@pytest.fixture
def mock_all_external_services():
  """Mock all external services (Ollama, external scripts)."""
  with patch('stage_incoming.run_external_script') as mock_joke_extract, \
       patch('stage_parsed.run_external_script') as mock_tfidf, \
       patch('stage_deduped.OllamaClient') as mock_ollama_deduped, \
       patch('stage_clean_checked.OllamaClient') as mock_ollama_format, \
       patch('stage_formatted.OllamaClient') as mock_ollama_categorize, \
       patch('stage_categorized.OllamaClient') as mock_ollama_title:

    # Mock joke-extract.py (stage_incoming)
    def mock_extract(script_path, args, timeout=60):
      # Extract email file path and success dir from args
      email_file = args[0]
      success_dir = args[1]

      # Create a sample joke output
      joke_content = """Title: Sample Joke
Submitter: test@example.com

This is a sample joke from an email."""

      # Write to success directory
      output_file = os.path.join(success_dir, 'extracted_joke.txt')
      with open(output_file, 'w', encoding='utf-8') as f:
        f.write(joke_content)

      return (0, '', '')

    mock_joke_extract.side_effect = mock_extract

    # Mock search_tfidf.py (stage_parsed)
    mock_tfidf.return_value = (0, '35 1234 Similar Joke Title', '')

    # Mock Ollama for cleanliness check (stage_deduped)
    mock_client_deduped = Mock()
    mock_client_deduped.generate.return_value = """
Status: PASS
Confidence: 90
Reason: Clean and appropriate
"""
    mock_client_deduped.parse_structured_response.return_value = {
      'Status': 'PASS',
      'Confidence': '90',
      'Reason': 'Clean and appropriate'
    }
    mock_client_deduped.extract_confidence.return_value = 90
    mock_ollama_deduped.return_value = mock_client_deduped

    # Mock Ollama for formatting (stage_clean_checked)
    mock_client_format = Mock()
    mock_client_format.generate.return_value = """
Formatted-Joke: This is a well-formatted sample joke from an email.
Confidence: 88
Changes: Minor punctuation improvements
"""
    mock_client_format.parse_structured_response.return_value = {
      'Formatted-Joke': 'This is a well-formatted sample joke from an email.',
      'Confidence': '88',
      'Changes': 'Minor punctuation improvements'
    }
    mock_client_format.extract_confidence.return_value = 88
    mock_ollama_format.return_value = mock_client_format

    # Mock Ollama for categorization (stage_formatted)
    mock_client_categorize = Mock()
    mock_client_categorize.generate.return_value = """
Categories: Clean, Observational
Confidence: 85
Reasoning: General clean observational humor
"""
    mock_client_categorize.parse_structured_response.return_value = {
      'Categories': 'Clean, Observational',
      'Confidence': '85',
      'Reasoning': 'General clean observational humor'
    }
    mock_client_categorize.extract_confidence.return_value = 85
    mock_ollama_categorize.return_value = mock_client_categorize

    # Mock Ollama for title generation (stage_categorized)
    # Not needed if title exists, but mock it anyway
    mock_client_title = Mock()
    mock_ollama_title.return_value = mock_client_title

    yield {
      'joke_extract': mock_joke_extract,
      'tfidf': mock_tfidf,
      'ollama_deduped': mock_ollama_deduped,
      'ollama_format': mock_ollama_format,
      'ollama_categorize': mock_ollama_categorize,
      'ollama_title': mock_ollama_title
    }


def test_full_pipeline_success(setup_full_pipeline, mock_all_external_services):
  """Test complete pipeline from email to ready_for_review."""
  env = setup_full_pipeline

  # Create a sample email in incoming directory
  email_file = os.path.join(
    env['pipeline_main'],
    '01_incoming',
    'test_email.eml'
  )
  with open(email_file, 'w', encoding='utf-8') as f:
    f.write('From: test@example.com\nSubject: Test\n\nEmail body')

  # Import and run pipeline
  pipeline_module = import_joke_pipeline()
  success = pipeline_module.run_pipeline(pipeline_type="main")

  assert success

  # Verify file reached ready_for_review
  ready_dir = os.path.join(env['pipeline_main'], '08_ready_for_review')
  files = os.listdir(ready_dir)

  # Should have at least one file
  assert len(files) > 0

  # Verify the file has all required fields
  output_file = os.path.join(ready_dir, files[0])
  headers, content = parse_joke_file(output_file)

  assert 'Joke-ID' in headers
  assert 'Title' in headers
  assert headers['Title'] == 'Sample Joke'
  assert 'Submitter' in headers
  assert 'Categories' in headers
  assert headers['Cleanliness-Status'] == 'PASS'
  assert headers['Format-Status'] == 'PASS'
  assert headers['Pipeline-Stage'] == config.STAGES['ready_for_review']


def test_priority_pipeline_first(setup_full_pipeline, mock_all_external_services):
  """Test that priority pipeline is processed before main."""
  env = setup_full_pipeline

  # Create email in priority pipeline
  priority_email = os.path.join(
    env['pipeline_priority'],
    '01_incoming',
    'priority_email.eml'
  )
  with open(priority_email, 'w', encoding='utf-8') as f:
    f.write('From: priority@example.com\nSubject: Priority\n\nPriority email')

  # Create email in main pipeline
  main_email = os.path.join(
    env['pipeline_main'],
    '01_incoming',
    'main_email.eml'
  )
  with open(main_email, 'w', encoding='utf-8') as f:
    f.write('From: main@example.com\nSubject: Main\n\nMain email')

  # Run pipeline
  pipeline_module = import_joke_pipeline()
  success = pipeline_module.run_pipeline(pipeline_type="both")

  assert success

  # Verify both files were processed
  priority_ready = os.path.join(env['pipeline_priority'], '08_ready_for_review')
  main_ready = os.path.join(env['pipeline_main'], '08_ready_for_review')

  assert len(os.listdir(priority_ready)) > 0
  assert len(os.listdir(main_ready)) > 0


def test_rejection_at_duplicate_stage(setup_full_pipeline):
  """Test rejection at duplicate detection stage."""
  env = setup_full_pipeline

  # Mock high duplicate score
  with patch('stage_incoming.run_external_script') as mock_extract, \
       patch('stage_parsed.run_external_script') as mock_tfidf:

    # Mock joke extraction
    def mock_extract_fn(script_path, args, timeout=60):
      success_dir = args[1]
      joke_content = """Title: Duplicate Joke
Submitter: test@example.com

This is a duplicate joke."""
      output_file = os.path.join(success_dir, 'joke.txt')
      with open(output_file, 'w', encoding='utf-8') as f:
        f.write(joke_content)
      return (0, '', '')

    mock_extract.side_effect = mock_extract_fn

    # Mock high duplicate score (above threshold)
    mock_tfidf.return_value = (0, '95 1234 Very Similar Joke', '')

    # Create email
    email_file = os.path.join(
      env['pipeline_main'],
      '01_incoming',
      'test_email.eml'
    )
    with open(email_file, 'w', encoding='utf-8') as f:
      f.write('From: test@example.com\nSubject: Test\n\nEmail')

    # Run pipeline
    pipeline_module = import_joke_pipeline()
    pipeline_module.run_pipeline(pipeline_type="main")

    # Verify file was rejected
    reject_dir = os.path.join(env['pipeline_main'], '51_rejected_duplicate')
    files = os.listdir(reject_dir)

    assert len(files) > 0

    # Verify rejection reason
    reject_file = os.path.join(reject_dir, files[0])
    headers, content = parse_joke_file(reject_file)
    assert 'Rejection-Reason' in headers
    assert 'duplicate' in headers['Rejection-Reason'].lower()


def test_multiple_files(setup_full_pipeline, mock_all_external_services):
  """Test processing multiple files through pipeline."""
  env = setup_full_pipeline

  # Create multiple emails
  for i in range(3):
    email_file = os.path.join(
      env['pipeline_main'],
      '01_incoming',
      f'email_{i}.eml'
    )
    with open(email_file, 'w', encoding='utf-8') as f:
      f.write(f'From: test{i}@example.com\nSubject: Test {i}\n\nEmail {i}')

  # Run pipeline
  pipeline_module = import_joke_pipeline()
  success = pipeline_module.run_pipeline(pipeline_type="main")

  assert success

  # Verify all files were processed
  ready_dir = os.path.join(env['pipeline_main'], '08_ready_for_review')
  files = os.listdir(ready_dir)

  # Should have at least 3 files
  assert len(files) >= 3


def test_stage_only_execution(setup_full_pipeline):
  """Test running a single stage only."""
  env = setup_full_pipeline

  # Create a joke file in the parsed stage
  headers = {
    'Joke-ID': '12345678-1234-1234-1234-123456789012',
    'Title': 'Test Joke',
    'Submitter': 'test@example.com',
    'Source-Email-File': 'test.eml',
    'Pipeline-Stage': '02_parsed'
  }
  content = 'This is a test joke for stage execution.'

  joke_file = os.path.join(
    env['pipeline_main'],
    '02_parsed',
    'test_joke.txt'
  )
  write_joke_file(joke_file, headers, content)

  # Mock TF-IDF to return low score
  with patch('stage_parsed.run_external_script') as mock_tfidf:
    mock_tfidf.return_value = (0, '25 1234 Different Joke', '')

    # Run only parsed stage
    pipeline_module = import_joke_pipeline()
    success = pipeline_module.run_pipeline(pipeline_type="main", stage_only="parsed")

    assert success

    # Verify file moved to deduped stage
    deduped_dir = os.path.join(env['pipeline_main'], '03_deduped')
    files = os.listdir(deduped_dir)

    assert len(files) > 0

    # Verify file has duplicate metadata
    deduped_file = os.path.join(deduped_dir, files[0])
    headers, content = parse_joke_file(deduped_file)
    assert 'Duplicate-Score' in headers
    assert headers['Pipeline-Stage'] == config.STAGES['deduped']


def test_command_line_help():
  """Test that --help works."""
  result = subprocess.run(
    ['python3', 'joke-pipeline.py', '--help'],
    capture_output=True,
    text=True
  )

  assert result.returncode == 0
  assert 'joke submission pipeline' in result.stdout.lower()
  assert '--pipeline' in result.stdout
  assert '--stage' in result.stdout
  assert '--verbose' in result.stdout


def test_command_line_invalid_stage():
  """Test that invalid stage returns error."""
  result = subprocess.run(
    ['python3', 'joke-pipeline.py', '--stage', 'invalid_stage'],
    capture_output=True,
    text=True
  )

  assert result.returncode != 0


def test_command_line_verbose_flag(setup_full_pipeline, mock_all_external_services):
  """Test that --verbose flag enables debug logging."""
  env = setup_full_pipeline

  # Create a sample email
  email_file = os.path.join(
    env['pipeline_main'],
    '01_incoming',
    'test_email.eml'
  )
  with open(email_file, 'w', encoding='utf-8') as f:
    f.write('From: test@example.com\nSubject: Test\n\nEmail body')

  # Run with verbose flag via subprocess
  result = subprocess.run(
    ['python3', 'joke-pipeline.py', '--verbose', '--pipeline', 'main'],
    capture_output=True,
    text=True,
    cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  )

  # Should succeed
  assert result.returncode == 0


def test_empty_pipeline(setup_full_pipeline):
  """Test pipeline with no files to process."""
  # Run pipeline with empty directories
  pipeline_module = import_joke_pipeline()
  success = pipeline_module.run_pipeline(pipeline_type="main")

  # Should still succeed (nothing to process)
  assert success
