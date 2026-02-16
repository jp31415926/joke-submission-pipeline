#!/usr/bin/env python3
"""
Tests for stage_parsed.py (Stage 02: Duplicate Detection)
"""

import os
import sys
import tempfile
import shutil
import pytest
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stage_parsed import ParsedProcessor
from file_utils import parse_joke_file, atomic_write
import config


@pytest.fixture
def temp_pipeline_dirs():
  """Create temporary pipeline directories for testing."""
  temp_dir = tempfile.mkdtemp()
  
  # Create pipeline-main structure
  pipeline_main = os.path.join(temp_dir, "pipeline-main")
  os.makedirs(pipeline_main)
  
  # Create all necessary directories
  parsed_dir = os.path.join(pipeline_main, config.STAGES["parsed"])
  deduped_dir = os.path.join(pipeline_main, config.STAGES["deduped"])
  rejected_dir = os.path.join(pipeline_main, config.REJECTS["duplicate"])
  
  os.makedirs(parsed_dir)
  os.makedirs(deduped_dir)
  os.makedirs(rejected_dir)
  
  # Also create tmp subdirectories as stage_processor expects
  os.makedirs(os.path.join(parsed_dir, 'tmp'))
  os.makedirs(os.path.join(deduped_dir, 'tmp'))
  
  # Create pipeline-priority structure (even if empty, to avoid path issues)
  pipeline_priority = os.path.join(temp_dir, "pipeline-priority")
  os.makedirs(pipeline_priority)
  
  # Override config paths
  original_main = config.PIPELINE_MAIN
  original_priority = config.PIPELINE_PRIORITY
  config.PIPELINE_MAIN = pipeline_main
  config.PIPELINE_PRIORITY = pipeline_priority
  
  yield {
    'pipeline_main': pipeline_main,
    'pipeline_priority': pipeline_priority,
    'parsed': parsed_dir,
    'deduped': deduped_dir,
    'rejected': rejected_dir
  }
  
  # Restore original config
  config.PIPELINE_MAIN = original_main
  config.PIPELINE_PRIORITY = original_priority
  
  # Cleanup
  shutil.rmtree(temp_dir)


@pytest.fixture
def mock_tfidf_script():
  """Set up mock search_tfidf.py script."""
  # Get path to mock script
  fixtures_dir = os.path.join(os.path.dirname(__file__), 'fixtures')
  mock_script = os.path.join(fixtures_dir, 'mock_search_tfidf.py')
  
  # Override config to use mock script
  original_script = config.SEARCH_TFIDF
  config.SEARCH_TFIDF = mock_script
  
  yield mock_script
  
  # Restore original config
  config.SEARCH_TFIDF = original_script


def create_test_joke(joke_dir, joke_id, content):
  """Helper to create a test joke file."""
  headers = {
    'Joke-ID': str(joke_id),
    'Pipeline-Stage': config.STAGES["parsed"],
    'Source': 'test',
    'Date-Received': '2024-01-01'
  }
  
  filepath = os.path.join(joke_dir, f"joke_{joke_id}.txt")
  atomic_write(filepath, headers, content)
  return filepath


def test_below_threshold(temp_pipeline_dirs, mock_tfidf_script):
  """Test joke with duplicate score below threshold passes."""
  # Set mock score to 30 (below threshold of 70)
  os.environ['MOCK_SCORE'] = '30'
  
  # Create test joke
  joke_file = create_test_joke(
    temp_pipeline_dirs['parsed'],
    1001,
    "Why did the chicken cross the road? To get to the other side!"
  )
  
  # Process
  processor = ParsedProcessor()
  processor.run()
  
  # Check file moved to deduped
  deduped_files = os.listdir(temp_pipeline_dirs['deduped'])
  assert len(deduped_files) == 1
  
  # Verify metadata
  deduped_file = os.path.join(temp_pipeline_dirs['deduped'], deduped_files[0])
  headers, _ = parse_joke_file(deduped_file)
  
  assert headers['Duplicate-Score'] == '30'
  assert headers['Duplicate-Threshold'] == '70'
  assert headers['Pipeline-Stage'] == config.STAGES["deduped"]
  
  # Check rejected directory is empty
  rejected_files = os.listdir(temp_pipeline_dirs['rejected'])
  assert len(rejected_files) == 0
  
  # Cleanup env
  del os.environ['MOCK_SCORE']


def test_at_threshold(temp_pipeline_dirs, mock_tfidf_script):
  """Test joke with duplicate score exactly at threshold is rejected."""
  # Set mock score to 70 (at threshold)
  os.environ['MOCK_SCORE'] = '70'
  
  # Create test joke
  joke_file = create_test_joke(
    temp_pipeline_dirs['parsed'],
    1002,
    "This is a duplicate joke."
  )
  
  # Process
  processor = ParsedProcessor()
  processor.run()
  
  # Check file moved to rejected
  rejected_files = os.listdir(temp_pipeline_dirs['rejected'])
  assert len(rejected_files) == 1
  
  # Verify metadata
  rejected_file = os.path.join(temp_pipeline_dirs['rejected'], rejected_files[0])
  headers, _ = parse_joke_file(rejected_file)
  
  assert headers['Duplicate-Score'] == '70'
  assert headers['Duplicate-Threshold'] == '70'
  assert headers['Pipeline-Stage'] == config.REJECTS["duplicate"]
  assert 'Duplicate score 70 >= threshold 70' in headers['Rejection-Reason']
  
  # Check deduped directory is empty
  deduped_files = os.listdir(temp_pipeline_dirs['deduped'])
  assert len(deduped_files) == 0
  
  # Cleanup env
  del os.environ['MOCK_SCORE']


def test_above_threshold(temp_pipeline_dirs, mock_tfidf_script):
  """Test joke with duplicate score above threshold is rejected."""
  # Set mock score to 95 (well above threshold)
  os.environ['MOCK_SCORE'] = '95'
  
  # Create test joke
  joke_file = create_test_joke(
    temp_pipeline_dirs['parsed'],
    1003,
    "This is definitely a duplicate."
  )
  
  # Process
  processor = ParsedProcessor()
  processor.run()
  
  # Check file moved to rejected
  rejected_files = os.listdir(temp_pipeline_dirs['rejected'])
  assert len(rejected_files) == 1
  
  # Verify metadata
  rejected_file = os.path.join(temp_pipeline_dirs['rejected'], rejected_files[0])
  headers, _ = parse_joke_file(rejected_file)
  
  assert headers['Duplicate-Score'] == '95'
  assert headers['Duplicate-Threshold'] == '70'
  assert headers['Pipeline-Stage'] == config.REJECTS["duplicate"]
  assert 'Duplicate score 95 >= threshold 70' in headers['Rejection-Reason']
  
  # Cleanup env
  del os.environ['MOCK_SCORE']


def test_metadata_updates(temp_pipeline_dirs, mock_tfidf_script):
  """Test that Duplicate-Score and Duplicate-Threshold are added to headers."""
  # Set mock score to 50
  os.environ['MOCK_SCORE'] = '50'
  
  # Create test joke
  joke_file = create_test_joke(
    temp_pipeline_dirs['parsed'],
    1004,
    "A joke to test metadata."
  )
  
  # Process
  processor = ParsedProcessor()
  processor.run()
  
  # Check file moved to deduped
  deduped_files = os.listdir(temp_pipeline_dirs['deduped'])
  assert len(deduped_files) == 1
  
  # Verify metadata exists and has correct values
  deduped_file = os.path.join(temp_pipeline_dirs['deduped'], deduped_files[0])
  headers, _ = parse_joke_file(deduped_file)
  
  assert 'Duplicate-Score' in headers
  assert 'Duplicate-Threshold' in headers
  assert headers['Duplicate-Score'] == '50'
  assert headers['Duplicate-Threshold'] == str(config.DUPLICATE_THRESHOLD)
  
  # Cleanup env
  del os.environ['MOCK_SCORE']


def test_search_tfidf_failure(temp_pipeline_dirs):
  """Test handling of search_tfidf.py failure."""
  # Create a mock script that fails
  temp_script = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py')
  temp_script.write("#!/usr/bin/env python3\n")
  temp_script.write("import sys\n")
  temp_script.write("print('Error occurred', file=sys.stderr)\n")
  temp_script.write("sys.exit(1)\n")
  temp_script.close()
  os.chmod(temp_script.name, 0o755)
  
  # Override config to use failing script
  original_script = config.SEARCH_TFIDF
  config.SEARCH_TFIDF = temp_script.name
  
  try:
    # Create test joke
    joke_file = create_test_joke(
      temp_pipeline_dirs['parsed'],
      1005,
      "A joke to test error handling."
    )
    
    # Process
    processor = ParsedProcessor()
    processor.run()
    
    # Check file moved to rejected
    rejected_files = os.listdir(temp_pipeline_dirs['rejected'])
    assert len(rejected_files) == 1
    
    # Verify rejection reason
    rejected_file = os.path.join(temp_pipeline_dirs['rejected'], rejected_files[0])
    headers, _ = parse_joke_file(rejected_file)
    
    assert 'Rejection-Reason' in headers
    assert 'search_tfidf.py failed' in headers['Rejection-Reason']
    
  finally:
    # Cleanup
    config.SEARCH_TFIDF = original_script
    os.remove(temp_script.name)


def test_multiple_jokes(temp_pipeline_dirs, mock_tfidf_script):
  """Test processing multiple jokes with different scores."""
  # Create multiple test jokes
  create_test_joke(temp_pipeline_dirs['parsed'], 2001, "Joke 1")
  create_test_joke(temp_pipeline_dirs['parsed'], 2002, "Joke 2")
  create_test_joke(temp_pipeline_dirs['parsed'], 2003, "Joke 3")
  
  # Set score below threshold
  os.environ['MOCK_SCORE'] = '40'
  
  # Process
  processor = ParsedProcessor()
  processor.run()
  
  # All should pass
  deduped_files = os.listdir(temp_pipeline_dirs['deduped'])
  assert len(deduped_files) == 3
  
  # Cleanup env
  del os.environ['MOCK_SCORE']


def test_edge_case_threshold_minus_one(temp_pipeline_dirs, mock_tfidf_script):
  """Test joke with score just below threshold passes."""
  # Set mock score to 69 (just below threshold of 70)
  os.environ['MOCK_SCORE'] = '69'
  
  # Create test joke
  create_test_joke(
    temp_pipeline_dirs['parsed'],
    3001,
    "Almost a duplicate."
  )
  
  # Process
  processor = ParsedProcessor()
  processor.run()
  
  # Should pass
  deduped_files = os.listdir(temp_pipeline_dirs['deduped'])
  assert len(deduped_files) == 1
  
  # Should not be rejected
  rejected_files = os.listdir(temp_pipeline_dirs['rejected'])
  assert len(rejected_files) == 0
  
  # Cleanup env
  del os.environ['MOCK_SCORE']
