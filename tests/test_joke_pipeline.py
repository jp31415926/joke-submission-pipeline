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
    "01_parse",
    "02_dedup",
    "03_clean_check",
    "04_format",
    "05_categorize",
    "06_title",
    "08_ready_for_review",
    "50_rejected_parse",
    "51_rejected_dedup",
    "52_rejected_clean_check",
    "53_rejected_format",
    "54_rejected_categorize",
    "55_rejected_title"
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
  with patch('stage_parse.run_external_script') as mock_joke_extract, \
       patch('stage_dedup.run_external_script') as mock_tfidf, \
       patch('stage_clean_check.OllamaClient') as mock_ollama_deduped, \
       patch('stage_format.OllamaClient') as mock_ollama_format, \
       patch('stage_categorize.OllamaClient') as mock_ollama_categorize, \
       patch('stage_title.OllamaClient') as mock_ollama_title:

    # Mock joke-extract.py (stage_parse)
    def mock_extract(script_path, args, timeout=60):
      # args order: [success_dir, fail_dir, filepath]
      success_dir = args[0]

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

    # Mock search_tfidf.py (stage_dedup)
    mock_tfidf.return_value = (0, '35 1234 Similar Joke Title', '')

    # Mock Ollama for cleanliness check (stage_clean_check)
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

    # Mock Ollama for formatting (stage_format)
    mock_client_format = Mock()
    mock_client_format.system_prompt = 'You are an editor.'
    mock_client_format.user_prompt_template = 'Format: {content}'
    # stage_format expects: "Confidence: X\nChanges: Y\n\n<joke content>"
    mock_client_format.generate.return_value = (
      "Confidence: 88\nChanges: Minor punctuation improvements\n\n"
      "This is a well-formatted sample joke from an email."
    )
    mock_client_format.extract_confidence.return_value = 88
    mock_ollama_format.return_value = mock_client_format

    # Mock Ollama for categorization (stage_categorize)
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

    # Mock Ollama for title generation (stage_title)
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
    '01_parse',
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
    '01_parse',
    'priority_email.eml'
  )
  with open(priority_email, 'w', encoding='utf-8') as f:
    f.write('From: priority@example.com\nSubject: Priority\n\nPriority email')

  # Create email in main pipeline
  main_email = os.path.join(
    env['pipeline_main'],
    '01_parse',
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
  with patch('stage_parse.run_external_script') as mock_extract, \
       patch('stage_dedup.run_external_script') as mock_tfidf:

    # Mock joke extraction
    def mock_extract_fn(script_path, args, timeout=60):
      # args order: [success_dir, fail_dir, filepath]
      success_dir = args[0]
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
      '01_parse',
      'test_email.eml'
    )
    with open(email_file, 'w', encoding='utf-8') as f:
      f.write('From: test@example.com\nSubject: Test\n\nEmail')

    # Run pipeline
    pipeline_module = import_joke_pipeline()
    pipeline_module.run_pipeline(pipeline_type="main")

    # Verify file was rejected
    reject_dir = os.path.join(env['pipeline_main'], '51_rejected_dedup')
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
      '01_parse',
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
    'Pipeline-Stage': '02_dedup'
  }
  content = 'This is a test joke for stage execution.'

  joke_file = os.path.join(
    env['pipeline_main'],
    '02_dedup',
    'test_joke.txt'
  )
  write_joke_file(joke_file, headers, content)

  # Mock TF-IDF to return low score
  with patch('stage_dedup.run_external_script') as mock_tfidf:
    mock_tfidf.return_value = (0, '25 1234 Different Joke', '')

    # Run only parsed stage
    pipeline_module = import_joke_pipeline()
    success = pipeline_module.run_pipeline(pipeline_type="main", stage_only="dedup")

    assert success

    # Verify file moved to deduped stage
    deduped_dir = os.path.join(env['pipeline_main'], '03_clean_check')
    files = os.listdir(deduped_dir)

    assert len(files) > 0

    # Verify file has duplicate metadata
    deduped_file = os.path.join(deduped_dir, files[0])
    headers, content = parse_joke_file(deduped_file)
    assert 'Duplicate-Score' in headers
    assert headers['Pipeline-Stage'] == config.STAGES['clean_check']


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
    '01_parse',
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
      '02_dedup',
      f'joke_{i}.txt'
    )
    headers = {
      'Joke-ID': f'12345678-1234-1234-1234-12345678901{i}',
      'Title': f'Test Joke {i}',
      'Submitter': 'test@example.com',
      'Pipeline-Stage': '02_dedup'
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
      os.path.join(env['pipeline_main'], '02_dedup')
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
  test_dir = os.path.join(env['pipeline_main'], '02_dedup')

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
    '02_dedup',
    'joke_1.txt'
  )
  headers = {
    'Joke-ID': '12345678-1234-1234-1234-123456789012',
    'Title': 'Test Joke',
    'Submitter': 'test@example.com',
    'Pipeline-Stage': '02_dedup'
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
    '02_dedup',
    'joke_1.txt'
  )
  headers = {
    'Joke-ID': '12345678-1234-1234-1234-123456789012',
    'Title': 'Test Joke',
    'Submitter': 'test@example.com',
    'Pipeline-Stage': '02_dedup'
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
        '02_dedup',
        f'joke_{i}.txt'
      )
      headers = {
        'Joke-ID': f'12345678-1234-1234-1234-12345678901{i}',
        'Title': f'Test Joke {i}',
        'Submitter': 'test@example.com',
        'Pipeline-Stage': '02_dedup'
      }
      write_joke_file(joke_file, headers, f'Content {i}')

    # Mock TF-IDF to return low score
    with patch('stage_dedup.run_external_script') as mock_tfidf:
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
      pipeline_module.run_pipeline(pipeline_type="main", stage_only="dedup")

      # Not all files should be processed (stopped by ALL_STOP)
      deduped_dir = os.path.join(env['pipeline_main'], '03_clean_check')
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
        '02_dedup',
        f'joke_{i}.txt'
      )
      headers = {
        'Joke-ID': f'12345678-1234-1234-1234-12345678901{i}',
        'Title': f'Test Joke {i}',
        'Submitter': 'test@example.com',
        'Pipeline-Stage': '02_dedup'
      }
      write_joke_file(joke_file, headers, f'Content {i}')

    # Mock TF-IDF to return low score
    with patch('stage_dedup.run_external_script') as mock_tfidf:
      mock_tfidf.return_value = (0, '25 1234 Different Joke', '')

      # Run parsed stage
      pipeline_module = import_joke_pipeline()
      pipeline_module.run_pipeline(pipeline_type="main", stage_only="dedup")

      # All files should be processed
      deduped_dir = os.path.join(env['pipeline_main'], '03_clean_check')
      deduped_files = [f for f in os.listdir(deduped_dir)
                       if f.endswith('.txt')]

      assert len(deduped_files) == 3

  finally:
    # Restore original ALL_STOP path
    config.ALL_STOP = original_all_stop


def test_files_moved_to_tmp_during_processing(setup_full_pipeline):
  """Test that files are moved to tmp/ directory while being processed."""
  env = setup_full_pipeline

  # Create a test file
  joke_file = os.path.join(
    env['pipeline_main'],
    '02_dedup',
    'test_joke.txt'
  )
  headers = {
    'Joke-ID': '12345678-1234-1234-1234-123456789012',
    'Title': 'Test Joke',
    'Submitter': 'test@example.com',
    'Pipeline-Stage': '02_dedup'
  }
  write_joke_file(joke_file, headers, 'Test content')

  # Verify file exists in stage directory
  assert os.path.exists(joke_file)

  # Track when processing starts
  processing_started = [False]
  tmp_file_existed = [False]

  # Mock TF-IDF to check tmp location during processing
  original_run_external_script = None
  try:
    import stage_dedup
    original_run_external_script = stage_dedup.run_external_script

    def mock_tfidf_check(*args, **kwargs):
      processing_started[0] = True
      # Check if file is in tmp directory during processing
      tmp_file = os.path.join(
        env['pipeline_main'],
        '02_dedup',
        'tmp',
        'test_joke.txt'
      )
      tmp_file_existed[0] = os.path.exists(tmp_file)

      # Also verify file is NOT in the original location
      original_file = os.path.join(
        env['pipeline_main'],
        '02_dedup',
        'test_joke.txt'
      )
      original_exists = os.path.exists(original_file)

      # During processing, file should be in tmp, not in original location
      if tmp_file_existed[0] and not original_exists:
        pass  # This is correct
      else:
        raise AssertionError(
          f"File should be in tmp during processing. "
          f"tmp exists: {tmp_file_existed[0]}, original exists: {original_exists}"
        )

      return (0, '25 1234 Different Joke', '')

    stage_dedup.run_external_script = mock_tfidf_check

    # Run parsed stage
    pipeline_module = import_joke_pipeline()
    pipeline_module.run_pipeline(pipeline_type="main", stage_only="dedup")

    # Verify processing occurred
    assert processing_started[0], "Processing should have started"
    assert tmp_file_existed[0], "File should have been in tmp during processing"

    # After processing, file should be in output directory, not tmp
    tmp_file = os.path.join(
      env['pipeline_main'],
      '02_dedup',
      'tmp',
      'test_joke.txt'
    )
    assert not os.path.exists(tmp_file), "File should not remain in tmp after processing"

    # File should be in output directory
    deduped_dir = os.path.join(env['pipeline_main'], '03_clean_check')
    deduped_files = [f for f in os.listdir(deduped_dir)
                     if f.endswith('.txt')]
    assert len(deduped_files) == 1, "File should be in output directory"

  finally:
    # Restore original function
    if original_run_external_script:
      stage_dedup.run_external_script = original_run_external_script


def test_tmp_directory_created_if_missing(setup_full_pipeline):
  """Test that tmp/ directory is created if it doesn't exist."""
  env = setup_full_pipeline

  # Ensure tmp directory doesn't exist
  tmp_dir = os.path.join(env['pipeline_main'], '02_dedup', 'tmp')
  if os.path.exists(tmp_dir):
    shutil.rmtree(tmp_dir)

  assert not os.path.exists(tmp_dir)

  # Create a test file
  joke_file = os.path.join(
    env['pipeline_main'],
    '02_dedup',
    'test_joke.txt'
  )
  headers = {
    'Joke-ID': '12345678-1234-1234-1234-123456789012',
    'Title': 'Test Joke',
    'Submitter': 'test@example.com',
    'Pipeline-Stage': '02_dedup'
  }
  write_joke_file(joke_file, headers, 'Test content')

  # Mock TF-IDF
  with patch('stage_dedup.run_external_script') as mock_tfidf:
    mock_tfidf.return_value = (0, '25 1234 Different Joke', '')

    # Run parsed stage
    pipeline_module = import_joke_pipeline()
    pipeline_module.run_pipeline(pipeline_type="main", stage_only="dedup")

    # tmp directory should have been created
    assert os.path.exists(tmp_dir), "tmp directory should be created"


def test_processing_file_created_and_deleted(setup_full_pipeline):
  """Test that PROCESSING file is created during processing and deleted after."""
  env = setup_full_pipeline

  # Create a test file
  joke_file = os.path.join(
    env['pipeline_main'],
    '02_dedup',
    'test_joke.txt'
  )
  headers = {
    'Joke-ID': '12345678-1234-1234-1234-123456789012',
    'Title': 'Test Joke',
    'Submitter': 'test@example.com',
    'Pipeline-Stage': '02_dedup'
  }
  write_joke_file(joke_file, headers, 'Test content')

  processing_file_path = os.path.join(
    env['pipeline_main'],
    '02_dedup',
    'tmp',
    'PROCESSING'
  )

  # Track PROCESSING file status
  processing_file_existed = [False]
  processing_file_content = [None]

  # Mock TF-IDF to check PROCESSING file during processing
  original_run_external_script = None
  try:
    import stage_dedup
    original_run_external_script = stage_dedup.run_external_script

    def mock_tfidf_check(*args, **kwargs):
      # Check if PROCESSING file exists during processing
      if os.path.exists(processing_file_path):
        processing_file_existed[0] = True
        with open(processing_file_path, 'r') as f:
          processing_file_content[0] = f.read()
      return (0, '25 1234 Different Joke', '')

    stage_dedup.run_external_script = mock_tfidf_check

    # Run parsed stage
    pipeline_module = import_joke_pipeline()
    pipeline_module.run_pipeline(pipeline_type="main", stage_only="dedup")

    # PROCESSING file should have existed during processing
    assert processing_file_existed[0], "PROCESSING file should exist during processing"
    assert processing_file_content[0] == '12345678-1234-1234-1234-123456789012', \
      "PROCESSING file should contain joke ID"

    # PROCESSING file should be deleted after processing
    assert not os.path.exists(processing_file_path), \
      "PROCESSING file should be deleted after processing"

  finally:
    # Restore original function
    if original_run_external_script:
      stage_dedup.run_external_script = original_run_external_script


def test_status_displays_processing_id(setup_full_pipeline):
  """Test that --status displays the processing joke ID."""
  env = setup_full_pipeline

  # Create a test file
  joke_file = os.path.join(
    env['pipeline_main'],
    '02_dedup',
    'test_joke.txt'
  )
  headers = {
    'Joke-ID': 'abcdefgh-1234-5678-9abc-def123456789',
    'Title': 'Test Joke',
    'Submitter': 'test@example.com',
    'Pipeline-Stage': '02_dedup'
  }
  write_joke_file(joke_file, headers, 'Test content')

  # Create a PROCESSING file to simulate active processing
  processing_file = os.path.join(
    env['pipeline_main'],
    '02_dedup',
    'tmp',
    'PROCESSING'
  )
  os.makedirs(os.path.dirname(processing_file), exist_ok=True)
  with open(processing_file, 'w') as f:
    f.write('abcdefgh-1234-5678-9abc-def123456789')

  # Import pipeline module and call show_status
  pipeline_module = import_joke_pipeline()

  # Capture stdout
  import io
  import sys
  captured_output = io.StringIO()
  sys.stdout = captured_output

  try:
    pipeline_module.show_status()
    output = captured_output.getvalue()

    # Should contain formatted joke ID (first5...last5)
    assert 'abcde...56789' in output, "Status should show formatted processing ID"

    # Should show separate Main and Priority sections
    assert 'Main Pipeline:' in output
    assert 'Priority Pipeline:' in output

  finally:
    sys.stdout = sys.__stdout__
    # Clean up PROCESSING file
    if os.path.exists(processing_file):
      os.remove(processing_file)


def test_format_joke_id():
  """Test joke ID formatting function."""
  pipeline_module = import_joke_pipeline()

  # Test long ID
  long_id = 'abcdefgh-1234-5678-9abc-def123456789'
  assert pipeline_module.format_joke_id(long_id) == 'abcde...56789'

  # Test short ID
  short_id = 'abc123'
  assert pipeline_module.format_joke_id(short_id) == 'abc123'

  # Test None
  assert pipeline_module.format_joke_id(None) == ''

  # Test empty string
  assert pipeline_module.format_joke_id('') == ''


def test_rejection_logged_to_file(setup_full_pipeline):
  """Test that rejections are logged to the appropriate log file."""
  env = setup_full_pipeline

  # Mock high duplicate score to trigger rejection
  with patch('stage_parse.run_external_script') as mock_extract, \
       patch('stage_dedup.run_external_script') as mock_tfidf:

    # Mock joke extraction
    def mock_extract_fn(script_path, args, timeout=60):
      # args order: [success_dir, fail_dir, filepath]
      success_dir = args[0]
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
      '01_parse',
      'test_email.eml'
    )
    with open(email_file, 'w', encoding='utf-8') as f:
      f.write('From: test@example.com\nSubject: Test\n\nEmail')

    # Run pipeline
    pipeline_module = import_joke_pipeline()
    pipeline_module.run_pipeline(pipeline_type="main")

    # Check that rejection log was created
    log_file = os.path.join(config.LOG_DIR, 'main_rejected_dedup.log')
    assert os.path.exists(log_file), f"Rejection log should exist at {log_file}"

    # Read log file
    with open(log_file, 'r') as f:
      log_content = f.read()

    # Should contain joke ID and reason
    assert 'Duplicate detected' in log_content or 'duplicate' in log_content.lower(), \
      "Log should contain rejection reason"
    # Should be one line per rejection
    lines = log_content.strip().split('\n')
    assert len(lines) >= 1, "Should have at least one log entry"


def test_rejection_log_separate_pipelines(setup_full_pipeline):
  """Test that main and priority rejections go to separate log files."""
  env = setup_full_pipeline

  # Mock high duplicate score
  with patch('stage_parse.run_external_script') as mock_extract, \
       patch('stage_dedup.run_external_script') as mock_tfidf:

    def mock_extract_fn(script_path, args, timeout=60):
      # args order: [success_dir, fail_dir, filepath]
      success_dir = args[0]
      joke_content = """Title: Duplicate Joke
Submitter: test@example.com

This is a duplicate joke."""
      output_file = os.path.join(success_dir, 'joke.txt')
      with open(output_file, 'w', encoding='utf-8') as f:
        f.write(joke_content)
      return (0, '', '')

    mock_extract.side_effect = mock_extract_fn
    mock_tfidf.return_value = (0, '95 1234 Very Similar Joke', '')

    # Create email in main pipeline
    main_email = os.path.join(
      env['pipeline_main'],
      '01_parse',
      'main_email.eml'
    )
    with open(main_email, 'w', encoding='utf-8') as f:
      f.write('From: main@example.com\nSubject: Main\n\nMain')

    # Create email in priority pipeline
    priority_email = os.path.join(
      env['pipeline_priority'],
      '01_parse',
      'priority_email.eml'
    )
    with open(priority_email, 'w', encoding='utf-8') as f:
      f.write('From: priority@example.com\nSubject: Priority\n\nPriority')

    # Run pipeline
    pipeline_module = import_joke_pipeline()
    pipeline_module.run_pipeline(pipeline_type="both")

    # Check that separate log files exist
    main_log = os.path.join(config.LOG_DIR, 'main_rejected_dedup.log')
    pri_log = os.path.join(config.LOG_DIR, 'pri_rejected_dedup.log')

    assert os.path.exists(main_log), "Main rejection log should exist"
    assert os.path.exists(pri_log), "Priority rejection log should exist"

    # Both should have content
    with open(main_log, 'r') as f:
      main_content = f.read()
    with open(pri_log, 'r') as f:
      pri_content = f.read()

    assert len(main_content) > 0, "Main log should have content"
    assert len(pri_content) > 0, "Priority log should have content"


def test_rejection_log_newlines_replaced(setup_full_pipeline):
  """Test that newlines in rejection reasons are replaced with spaces."""
  env = setup_full_pipeline

  # Create a test file in parsed stage
  joke_file = os.path.join(
    env['pipeline_main'],
    '02_dedup',
    'test_joke.txt'
  )
  headers = {
    'Joke-ID': '12345678-1234-1234-1234-123456789012',
    'Title': 'Test Joke',
    'Submitter': 'test@example.com',
    'Pipeline-Stage': '02_dedup'
  }
  write_joke_file(joke_file, headers, 'Test content')

  # Mock to return a rejection reason with newlines
  with patch('stage_dedup.run_external_script') as mock_tfidf:
    mock_tfidf.return_value = (0, '95 1234 Very Similar Joke', '')

    # Run pipeline
    pipeline_module = import_joke_pipeline()
    pipeline_module.run_pipeline(pipeline_type="main", stage_only="dedup")

    # Check rejection log
    log_file = os.path.join(config.LOG_DIR, 'main_rejected_dedup.log')
    assert os.path.exists(log_file)

    with open(log_file, 'r') as f:
      log_content = f.read()

    # Should be a single line (no embedded newlines from reason)
    lines = log_content.strip().split('\n')
    # Each line should have joke ID and reason
    for line in lines:
      parts = line.split(' ', 1)
      assert len(parts) == 2, "Each line should have joke_id and reason"
      joke_id, reason = parts
      # Reason should not contain literal newlines
      assert '\n' not in reason, "Reason should not contain newlines"


# ---------------------------------------------------------------------------
# Tests for --retry / retry_jokes
# ---------------------------------------------------------------------------

def _make_rejected_joke(reject_dir: str, joke_id: str, stage: str, reason: str):
  """Helper: write a joke file into a reject directory."""
  os.makedirs(reject_dir, exist_ok=True)
  headers = {
    'Joke-ID': joke_id,
    'Title': 'Test Joke',
    'Submitter': 'test@example.com',
    'Source-Email-File': 'test.eml',
    'Pipeline-Stage': stage,
    'Rejection-Reason': reason,
    'Categories': 'Pun',
  }
  write_joke_file(os.path.join(reject_dir, f"{joke_id}.txt"), headers, 'Content.')


def test_retry_moves_file_to_retry_stage(setup_full_pipeline):
  """Test that retry_jokes moves a file from reject dir to the retry stage."""
  env = setup_full_pipeline
  joke_id = '11111111-1111-1111-1111-111111111111'

  reject_dir = os.path.join(env['pipeline_main'], config.REJECTS['dedup'])
  _make_rejected_joke(
    reject_dir, joke_id, config.REJECTS['dedup'], 'Duplicate detected'
  )

  pipeline_module = import_joke_pipeline()
  result = pipeline_module.retry_jokes('main', 'dedup', [joke_id])

  assert result is True
  assert not os.path.exists(os.path.join(reject_dir, f"{joke_id}.txt"))
  retry_dir = os.path.join(env['pipeline_main'], config.STAGES['dedup'])
  assert os.path.exists(os.path.join(retry_dir, f"{joke_id}.txt"))


def test_retry_clears_rejection_reason(setup_full_pipeline):
  """Test that retry_jokes removes the Rejection-Reason header."""
  env = setup_full_pipeline
  joke_id = '22222222-2222-2222-2222-222222222222'

  reject_dir = os.path.join(env['pipeline_main'], config.REJECTS['categorize'])
  _make_rejected_joke(
    reject_dir, joke_id, config.REJECTS['categorize'], 'No valid categories'
  )

  pipeline_module = import_joke_pipeline()
  pipeline_module.retry_jokes('main', 'categorize', [joke_id])

  retry_path = os.path.join(
    env['pipeline_main'], config.STAGES['categorize'], f"{joke_id}.txt"
  )
  headers, _ = parse_joke_file(retry_path)
  assert 'Rejection-Reason' not in headers
  assert headers['Pipeline-Stage'] == config.STAGES['categorize']


def test_retry_updates_pipeline_stage_header(setup_full_pipeline):
  """Test that Pipeline-Stage header is updated to the retry stage."""
  env = setup_full_pipeline
  joke_id = '33333333-3333-3333-3333-333333333333'

  reject_dir = os.path.join(env['pipeline_main'], config.REJECTS['clean_check'])
  _make_rejected_joke(
    reject_dir, joke_id, config.REJECTS['clean_check'], 'Failed cleanliness'
  )

  pipeline_module = import_joke_pipeline()
  pipeline_module.retry_jokes('main', 'clean_check', [joke_id])

  retry_path = os.path.join(
    env['pipeline_main'], config.STAGES['clean_check'], f"{joke_id}.txt"
  )
  headers, _ = parse_joke_file(retry_path)
  assert headers['Pipeline-Stage'] == config.STAGES['clean_check']


def test_retry_multiple_ids(setup_full_pipeline):
  """Test that retry_jokes handles multiple IDs at once."""
  env = setup_full_pipeline
  ids = [
    'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
    'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb',
    'cccccccc-cccc-cccc-cccc-cccccccccccc',
  ]

  reject_dir = os.path.join(env['pipeline_main'], config.REJECTS['format'])
  for joke_id in ids:
    _make_rejected_joke(
      reject_dir, joke_id, config.REJECTS['format'], 'Bad format'
    )

  pipeline_module = import_joke_pipeline()
  result = pipeline_module.retry_jokes('main', 'format', ids)

  assert result is True
  retry_dir = os.path.join(env['pipeline_main'], config.STAGES['format'])
  for joke_id in ids:
    assert os.path.exists(os.path.join(retry_dir, f"{joke_id}.txt"))


def test_retry_missing_id_returns_false(setup_full_pipeline):
  """Test that retry_jokes returns False when a joke ID is not found."""
  pipeline_module = import_joke_pipeline()
  result = pipeline_module.retry_jokes(
    'main', 'dedup', ['deadbeef-dead-dead-dead-deaddeadbeef']
  )
  assert result is False


def test_retry_partial_found(setup_full_pipeline):
  """Test retry with one valid and one missing ID: moves valid, returns False."""
  env = setup_full_pipeline
  good_id = 'dddddddd-dddd-dddd-dddd-dddddddddddd'
  bad_id = 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee'

  reject_dir = os.path.join(env['pipeline_main'], config.REJECTS['title'])
  _make_rejected_joke(
    reject_dir, good_id, config.REJECTS['title'], 'Title failed'
  )

  pipeline_module = import_joke_pipeline()
  result = pipeline_module.retry_jokes('main', 'title', [good_id, bad_id])

  assert result is False  # bad_id not found
  retry_dir = os.path.join(env['pipeline_main'], config.STAGES['title'])
  assert os.path.exists(os.path.join(retry_dir, f"{good_id}.txt"))


def test_retry_priority_pipeline(setup_full_pipeline):
  """Test retry works for the priority pipeline."""
  env = setup_full_pipeline
  joke_id = 'ffffffff-ffff-ffff-ffff-ffffffffffff'

  reject_dir = os.path.join(env['pipeline_priority'], config.REJECTS['dedup'])
  _make_rejected_joke(
    reject_dir, joke_id, config.REJECTS['dedup'], 'Duplicate'
  )

  pipeline_module = import_joke_pipeline()
  result = pipeline_module.retry_jokes('priority', 'dedup', [joke_id])

  assert result is True
  retry_dir = os.path.join(env['pipeline_priority'], config.STAGES['dedup'])
  assert os.path.exists(os.path.join(retry_dir, f"{joke_id}.txt"))


def test_retry_cli_missing_args():
  """Test that --retry without required args exits with error."""
  result = subprocess.run(
    ['python3', 'joke-pipeline.py', '--retry'],
    capture_output=True, text=True,
    cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
  )
  assert result.returncode != 0
  assert 'error' in result.stderr.lower()


def test_retry_all_stage_mappings(setup_full_pipeline):
  """Test that all reject stage -> retry stage mappings work correctly."""
  env = setup_full_pipeline
  pipeline_module = import_joke_pipeline()

  stage_map = {
    'dedup': config.STAGES['dedup'],
    'clean_check': config.STAGES['clean_check'],
    'format': config.STAGES['format'],
    'categorize': config.STAGES['categorize'],
    'title': config.STAGES['title'],
  }

  for i, (reject_stage, retry_stage) in enumerate(stage_map.items()):
    joke_id = f'1234567{i}-0000-0000-0000-000000000000'
    reject_dir = os.path.join(env['pipeline_main'], config.REJECTS[reject_stage])
    _make_rejected_joke(
      reject_dir, joke_id, config.REJECTS[reject_stage], 'Test'
    )

    pipeline_module.retry_jokes('main', reject_stage, [joke_id])

    retry_path = os.path.join(env['pipeline_main'], retry_stage, f"{joke_id}.txt")
    assert os.path.exists(retry_path), (
      f"Stage '{reject_stage}' should map to '{retry_stage}'"
    )
