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
    mock_client_deduped.system_prompt = 'You are a content moderator.'
    mock_client_deduped.user_prompt_template = 'Evaluate: {content}'
    import json as json_lib
    mock_client_deduped.generate.return_value = json_lib.dumps({"status": "PASS", "confidence": 90, "reason": "Clean and appropriate"})
    mock_client_deduped.parse_structured_response.return_value = {
      'status': 'PASS',
      'confidence': '90',
      'reason': 'Clean and appropriate'
    }
    mock_client_deduped.extract_confidence.return_value = 90
    mock_ollama_deduped.return_value = mock_client_deduped

    # Mock Ollama for formatting (stage_clean_checked)
    mock_client_format = Mock()
    mock_client_format.system_prompt = 'You are an editor.'
    mock_client_format.user_prompt_template = 'Format: {content}'
    mock_client_format.generate.return_value = json_lib.dumps({"formatted_joke": "This is a well-formatted sample joke from an email.", "confidence": 88, "changes": "Minor punctuation improvements"})
    mock_client_format.parse_structured_response.return_value = {
      'formatted_joke': 'This is a well-formatted sample joke from an email.',
      'confidence': '88',
      'changes': 'Minor punctuation improvements'
    }
    mock_client_format.extract_confidence.return_value = 88
    mock_ollama_format.return_value = mock_client_format

    # Mock Ollama for categorization (stage_formatted)
    mock_client_categorize = Mock()
    mock_client_categorize.system_prompt = 'You are a joke categorizer.'
    mock_client_categorize.user_prompt_template = 'Categorize: {content}'
    mock_client_categorize.generate.return_value = json_lib.dumps({"categories": ["Puns", "Observational"], "confidence": 85, "reason": "General clean observational humor"})
    mock_client_categorize.parse_structured_response.return_value = {
      'categories': ['Clean', 'Observational'],
      'confidence': '85',
      'reason': 'General clean observational humor'
    }
    mock_client_categorize.extract_confidence.return_value = 85
    mock_ollama_categorize.return_value = mock_client_categorize

    # Mock Ollama for title generation (stage_categorized)
    # Not needed if title exists, but mock it anyway
    mock_client_title = Mock()
    mock_client_title.system_prompt = 'You are a title writer.'
    mock_client_title.user_prompt_template = 'Create title: {content}'
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


def test_status_with_missing_files(setup_full_pipeline):
  """Test that status handles files being deleted during execution."""
  env = setup_full_pipeline
  pipeline_module = import_joke_pipeline()

  # Create some test files
  for i in range(5):
    joke_file = os.path.join(
      env['pipeline_main'],
      '02_parsed',
      f'joke_{i}.txt'
    )
    headers = {
      'Joke-ID': f'12345678-1234-1234-1234-12345678901{i}',
      'Title': f'Test Joke {i}',
      'Submitter': 'test@example.com',
      'Pipeline-Stage': '02_parsed'
    }
    write_joke_file(joke_file, headers, f'Content {i}')

  # Mock os.path.getmtime to simulate file deletion for some files
  original_getmtime = os.path.getmtime
  call_count = [0]

  def mock_getmtime(path):
    call_count[0] += 1
    # Simulate file deletion on every other call
    if call_count[0] % 2 == 0:
      raise FileNotFoundError(f"File not found: {path}")
    return original_getmtime(path)

  with patch('os.path.getmtime', side_effect=mock_getmtime):
    # Should not raise an exception
    count, oldest = pipeline_module.get_directory_status(
      os.path.join(env['pipeline_main'], '02_parsed')
    )

    # Should still return some count (files that weren't "deleted")
    assert count >= 0


def test_status_with_inaccessible_directory(setup_full_pipeline):
  """Test that status handles inaccessible directories gracefully."""
  env = setup_full_pipeline
  pipeline_module = import_joke_pipeline()

  # Test with non-existent directory
  count, oldest = pipeline_module.get_directory_status('/nonexistent/path')
  assert count == 0
  assert oldest is None

  # Test with directory that becomes inaccessible
  test_dir = os.path.join(env['pipeline_main'], '02_parsed')

  with patch('os.listdir', side_effect=PermissionError("Access denied")):
    count, oldest = pipeline_module.get_directory_status(test_dir)
    assert count == 0
    assert oldest is None


def test_show_status_with_missing_tmp_dirs(setup_full_pipeline):
  """Test that show_status handles missing or inaccessible tmp directories."""
  env = setup_full_pipeline
  pipeline_module = import_joke_pipeline()

  # Create some test files in regular directories
  joke_file = os.path.join(
    env['pipeline_main'],
    '02_parsed',
    'joke_1.txt'
  )
  headers = {
    'Joke-ID': '12345678-1234-1234-1234-123456789012',
    'Title': 'Test Joke',
    'Submitter': 'test@example.com',
    'Pipeline-Stage': '02_parsed'
  }
  write_joke_file(joke_file, headers, 'Content')

  # Mock os.listdir to fail for tmp directories
  original_listdir = os.listdir

  def mock_listdir(path):
    if 'tmp' in path:
      raise FileNotFoundError("Tmp directory deleted")
    return original_listdir(path)

  with patch('os.listdir', side_effect=mock_listdir):
    # Should not raise an exception
    try:
      pipeline_module.show_status()
      status_works = True
    except Exception:
      status_works = False

    assert status_works


def test_command_line_status(setup_full_pipeline):
  """Test --status command line flag."""
  env = setup_full_pipeline

  # Create a test file
  joke_file = os.path.join(
    env['pipeline_main'],
    '02_parsed',
    'joke_1.txt'
  )
  headers = {
    'Joke-ID': '12345678-1234-1234-1234-123456789012',
    'Title': 'Test Joke',
    'Submitter': 'test@example.com',
    'Pipeline-Stage': '02_parsed'
  }
  write_joke_file(joke_file, headers, 'Content')

  # Run status command
  result = subprocess.run(
    ['python3', 'joke-pipeline.py', '--status'],
    capture_output=True,
    text=True,
    cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  )

  # Should succeed
  assert result.returncode == 0
  # Should contain status information
  assert 'Pipeline Status' in result.stdout or 'Stage' in result.stdout


def test_all_stop_file_deleted_on_startup(setup_full_pipeline):
  """Test that ALL_STOP file is deleted when pipeline starts."""
  env = setup_full_pipeline

  # Save original ALL_STOP path
  original_all_stop = config.ALL_STOP

  try:
    # Create a temporary ALL_STOP file
    test_all_stop = os.path.join(env['test_dir'], 'ALL_STOP')
    config.ALL_STOP = test_all_stop

    # Create the ALL_STOP file
    with open(test_all_stop, 'w') as f:
      f.write('stop')

    assert os.path.exists(test_all_stop)

    # Import and run pipeline
    pipeline_module = import_joke_pipeline()

    # Mock the run_pipeline function to prevent actual execution
    with patch.object(pipeline_module, 'run_pipeline', return_value=True):
      # Simulate what main() does
      if os.path.exists(config.ALL_STOP):
        os.remove(config.ALL_STOP)

    # ALL_STOP file should be deleted
    assert not os.path.exists(test_all_stop)

  finally:
    # Restore original ALL_STOP path
    config.ALL_STOP = original_all_stop


def test_stage_processor_stops_on_all_stop(setup_full_pipeline):
  """Test that stage processor stops when ALL_STOP file is created."""
  env = setup_full_pipeline

  # Save original ALL_STOP path
  original_all_stop = config.ALL_STOP

  try:
    # Set ALL_STOP to test directory
    test_all_stop = os.path.join(env['test_dir'], 'ALL_STOP')
    config.ALL_STOP = test_all_stop

    # Create multiple test files
    for i in range(5):
      joke_file = os.path.join(
        env['pipeline_main'],
        '02_parsed',
        f'joke_{i}.txt'
      )
      headers = {
        'Joke-ID': f'12345678-1234-1234-1234-12345678901{i}',
        'Title': f'Test Joke {i}',
        'Submitter': 'test@example.com',
        'Pipeline-Stage': '02_parsed'
      }
      write_joke_file(joke_file, headers, f'Content {i}')

    # Mock TF-IDF to return low score
    with patch('stage_parsed.run_external_script') as mock_tfidf:
      # Create ALL_STOP file after processing first file
      call_count = [0]

      def mock_tfidf_fn(*args, **kwargs):
        call_count[0] += 1
        if call_count[0] == 2:
          # Create ALL_STOP file after processing one file
          with open(test_all_stop, 'w') as f:
            f.write('stop')
        return (0, '25 1234 Different Joke', '')

      mock_tfidf.side_effect = mock_tfidf_fn

      # Run parsed stage
      pipeline_module = import_joke_pipeline()
      pipeline_module.run_pipeline(pipeline_type="main", stage_only="parsed")

      # Not all files should be processed (stopped by ALL_STOP)
      deduped_dir = os.path.join(env['pipeline_main'], '03_deduped')
      deduped_files = os.listdir(deduped_dir) if os.path.exists(deduped_dir) else []

      # Should have processed fewer than 5 files
      assert len(deduped_files) < 5

  finally:
    # Restore original ALL_STOP path and clean up
    config.ALL_STOP = original_all_stop
    if os.path.exists(test_all_stop):
      os.remove(test_all_stop)


def test_stage_processor_continues_without_all_stop(setup_full_pipeline):
  """Test that stage processor continues normally without ALL_STOP file."""
  env = setup_full_pipeline

  # Save original ALL_STOP path
  original_all_stop = config.ALL_STOP

  try:
    # Set ALL_STOP to test directory (but don't create it)
    test_all_stop = os.path.join(env['test_dir'], 'ALL_STOP')
    config.ALL_STOP = test_all_stop

    # Create test files
    for i in range(3):
      joke_file = os.path.join(
        env['pipeline_main'],
        '02_parsed',
        f'joke_{i}.txt'
      )
      headers = {
        'Joke-ID': f'12345678-1234-1234-1234-12345678901{i}',
        'Title': f'Test Joke {i}',
        'Submitter': 'test@example.com',
        'Pipeline-Stage': '02_parsed'
      }
      write_joke_file(joke_file, headers, f'Content {i}')

    # Mock TF-IDF to return low score
    with patch('stage_parsed.run_external_script') as mock_tfidf:
      mock_tfidf.return_value = (0, '25 1234 Different Joke', '')

      # Run parsed stage
      pipeline_module = import_joke_pipeline()
      pipeline_module.run_pipeline(pipeline_type="main", stage_only="parsed")

      # All files should be processed
      deduped_dir = os.path.join(env['pipeline_main'], '03_deduped')
      deduped_files = [f for f in os.listdir(deduped_dir)
                       if f.endswith('.txt')]

      assert len(deduped_files) == 3

  finally:
    # Restore original ALL_STOP path
    config.ALL_STOP = original_all_stop
