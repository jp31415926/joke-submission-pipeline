#!/usr/bin/env python3
"""
Tests for stage_parse.py - Email extraction and joke creation.
"""

import os
import sys
import shutil
import tempfile
import re
import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stage_parse import ParseProcessor
from file_utils import parse_joke_file
import config


@pytest.fixture
def setup_test_environment():
    """Setup and teardown for each test."""
    # Create temporary directories for testing
    test_dir = tempfile.mkdtemp(prefix="test_parse_")
    pipeline_main = os.path.join(test_dir, "pipeline-main")
    pipeline_priority = os.path.join(test_dir, "pipeline-priority")
    
    # Create directory structure
    os.makedirs(os.path.join(pipeline_main, "01_parse"))
    os.makedirs(os.path.join(pipeline_main, "02_dedup"))
    os.makedirs(os.path.join(pipeline_main, "50_rejected_parse"))
    os.makedirs(os.path.join(pipeline_priority, "01_parse"))
    os.makedirs(os.path.join(pipeline_priority, "02_dedup"))
    os.makedirs(os.path.join(pipeline_priority, "50_rejected_parse"))
    
    # Store original config values
    orig_pipeline_main = config.PIPELINE_MAIN
    orig_pipeline_priority = config.PIPELINE_PRIORITY
    orig_joke_extractor = config.JOKE_EXTRACTOR
    
    # Update config to use test directories
    config.PIPELINE_MAIN = pipeline_main
    config.PIPELINE_PRIORITY = pipeline_priority
    
    # Use mock joke-extract.py
    mock_script = os.path.join(
        os.path.dirname(__file__),
        "fixtures",
        "mock_joke_extract.py"
    )
    config.JOKE_EXTRACTOR = mock_script
    
    # Yield the test environment
    yield {
        'test_dir': test_dir,
        'pipeline_main': pipeline_main,
        'pipeline_priority': pipeline_priority
    }
    
    # Restore original config
    config.PIPELINE_MAIN = orig_pipeline_main
    config.PIPELINE_PRIORITY = orig_pipeline_priority
    config.JOKE_EXTRACTOR = orig_joke_extractor
    
    # Clean up test directory
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)


def test_process_single_joke_email(setup_test_environment):
    """Test processing an email with a single joke."""
    env = setup_test_environment
    
    # Copy test email to incoming directory
    fixture_email = os.path.join(
        os.path.dirname(__file__),
        "fixtures",
        "emails",
        "sample_single_joke.eml"
    )
    test_email = os.path.join(
        env['pipeline_main'],
        "01_parse",
        "sample_single_joke.eml"
    )
    shutil.copy(fixture_email, test_email)
    
    # Create processor and run
    processor = ParseProcessor()
    processor.run()
    
    # Verify email was deleted from incoming
    assert not os.path.exists(test_email)
    
    # Verify joke file was created in parsed directory
    parsed_dir = os.path.join(env['pipeline_main'], "02_dedup")
    joke_files = [f for f in os.listdir(parsed_dir) if f.endswith('.txt')]
    assert len(joke_files) == 1
    
    # Parse the joke file
    joke_path = os.path.join(parsed_dir, joke_files[0])
    headers, content = parse_joke_file(joke_path)
    
    # Verify headers
    assert 'Joke-ID' in headers
    assert 'Source-Email-File' in headers
    assert headers['Source-Email-File'] == 'sample_single_joke.eml'
    assert headers['Pipeline-Stage'] == '02_dedup'
    assert headers['Title'] == 'Colorful Meal'
    assert 'Submitter' in headers
    
    # Verify content
    assert 'colorful meal' in content.lower()
    assert 'burned parts' in content.lower()


def test_process_multiple_jokes_email(setup_test_environment):
    """Test processing an email with multiple jokes."""
    env = setup_test_environment
    
    # Copy test email to incoming directory
    fixture_email = os.path.join(
        os.path.dirname(__file__),
        "fixtures",
        "emails",
        "sample_multiple_jokes.eml"
    )
    test_email = os.path.join(
        env['pipeline_main'],
        "01_parse",
        "sample_multiple_jokes.eml"
    )
    shutil.copy(fixture_email, test_email)
    
    # Create processor and run
    processor = ParseProcessor()
    processor.run()
    
    # Verify email was deleted from incoming
    assert not os.path.exists(test_email)
    
    # Verify two joke files were created in parsed directory
    parsed_dir = os.path.join(env['pipeline_main'], "02_dedup")
    joke_files = [f for f in os.listdir(parsed_dir) if f.endswith('.txt')]
    assert len(joke_files) == 2
    
    # Verify each joke has unique UUID
    joke_ids = []
    for joke_file in joke_files:
        joke_path = os.path.join(parsed_dir, joke_file)
        headers, content = parse_joke_file(joke_path)
        
        # Verify headers
        assert 'Joke-ID' in headers
        assert headers['Source-Email-File'] == 'sample_multiple_jokes.eml'
        assert headers['Pipeline-Stage'] == '02_dedup'
        
        joke_ids.append(headers['Joke-ID'])
    
    # Verify UUIDs are unique
    assert len(set(joke_ids)) == 2


def test_process_no_jokes_email(setup_test_environment):
    """Test processing an email with no jokes (should reject)."""
    env = setup_test_environment
    
    # Copy test email to incoming directory
    fixture_email = os.path.join(
        os.path.dirname(__file__),
        "fixtures",
        "emails",
        "sample_no_jokes.eml"
    )
    test_email = os.path.join(
        env['pipeline_main'],
        "01_parse",
        "sample_no_jokes.eml"
    )
    shutil.copy(fixture_email, test_email)
    
    # Create processor and run
    processor = ParseProcessor()
    processor.run()
    
    # Verify email was moved to reject directory
    assert not os.path.exists(test_email)
    
    # Verify no jokes in parsed directory
    parsed_dir = os.path.join(env['pipeline_main'], "02_dedup")
    joke_files = [f for f in os.listdir(parsed_dir) if f.endswith('.txt')]
    assert len(joke_files) == 0
    
    # Verify email in reject directory
    reject_dir = os.path.join(env['pipeline_main'], "50_rejected_parse")
    reject_files = [f for f in os.listdir(reject_dir) if f.endswith('.eml')]
    assert len(reject_files) == 1


def test_joke_extractor_failure(setup_test_environment):
    """Test handling of joke-extract.py failure."""
    env = setup_test_environment
    
    # Create a test email that will trigger failure in mock script
    test_email = os.path.join(
        env['pipeline_main'],
        "01_parse",
        "sample_fail.eml"
    )
    with open(test_email, 'w') as f:
        f.write("This email will trigger failure\n")
    
    # Create processor and run
    processor = ParseProcessor()
    processor.run()
    
    # Verify email was moved to reject directory
    assert not os.path.exists(test_email)
    
    # Verify email in reject directory
    reject_dir = os.path.join(env['pipeline_main'], "50_rejected_parse")
    reject_files = [f for f in os.listdir(reject_dir) if f.endswith('.eml')]
    assert len(reject_files) == 1


def test_uuid_generation(setup_test_environment):
    """Test that each joke gets a unique UUID."""
    env = setup_test_environment
    
    # Copy test email with multiple jokes
    fixture_email = os.path.join(
        os.path.dirname(__file__),
        "fixtures",
        "emails",
        "sample_multiple_jokes.eml"
    )
    test_email = os.path.join(
        env['pipeline_main'],
        "01_parse",
        "sample_multiple_jokes.eml"
    )
    shutil.copy(fixture_email, test_email)
    
    # Create processor and run
    processor = ParseProcessor()
    processor.run()
    
    # Get all joke files
    parsed_dir = os.path.join(env['pipeline_main'], "02_dedup")
    joke_files = [f for f in os.listdir(parsed_dir) if f.endswith('.txt')]
    
    # Verify each file has a UUID filename
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.txt$'
    )
    for joke_file in joke_files:
        assert uuid_pattern.match(joke_file), f"Invalid UUID filename: {joke_file}"
    
    # Verify Joke-ID in headers matches filename
    for joke_file in joke_files:
        joke_path = os.path.join(parsed_dir, joke_file)
        headers, content = parse_joke_file(joke_path)
        
        expected_id = joke_file.replace('.txt', '')
        assert headers['Joke-ID'] == expected_id


def test_metadata_initialization(setup_test_environment):
    """Test that metadata is properly initialized for each joke."""
    env = setup_test_environment
    
    # Copy test email
    fixture_email = os.path.join(
        os.path.dirname(__file__),
        "fixtures",
        "emails",
        "sample_single_joke.eml"
    )
    test_email = os.path.join(
        env['pipeline_main'],
        "01_parse",
        "test_metadata.eml"
    )
    shutil.copy(fixture_email, test_email)
    
    # Create processor and run
    processor = ParseProcessor()
    processor.run()
    
    # Get joke file
    parsed_dir = os.path.join(env['pipeline_main'], "02_dedup")
    joke_files = [f for f in os.listdir(parsed_dir) if f.endswith('.txt')]
    assert len(joke_files) == 1
    
    # Parse joke
    joke_path = os.path.join(parsed_dir, joke_files[0])
    headers, content = parse_joke_file(joke_path)
    
    # Verify required metadata fields
    assert 'Joke-ID' in headers
    assert 'Source-Email-File' in headers
    assert 'Pipeline-Stage' in headers
    
    # Verify values
    assert headers['Source-Email-File'] == 'test_metadata.eml'
    assert headers['Pipeline-Stage'] == '02_dedup'
    
    # Verify original headers preserved
    assert 'Title' in headers
    assert 'Submitter' in headers


def test_priority_pipeline(setup_test_environment):
    """Test that priority pipeline is processed correctly."""
    env = setup_test_environment
    
    # Copy test email to priority incoming directory
    fixture_email = os.path.join(
        os.path.dirname(__file__),
        "fixtures",
        "emails",
        "sample_single_joke.eml"
    )
    test_email = os.path.join(
        env['pipeline_priority'],
        "01_parse",
        "priority_joke.eml"
    )
    shutil.copy(fixture_email, test_email)
    
    # Create processor and run
    processor = ParseProcessor()
    processor.run()
    
    # Verify email was deleted from priority incoming
    assert not os.path.exists(test_email)
    
    # Verify joke file was created in priority parsed directory
    parsed_dir = os.path.join(env['pipeline_priority'], "02_dedup")
    joke_files = [f for f in os.listdir(parsed_dir) if f.endswith('.txt')]
    assert len(joke_files) == 1


def test_filesystem_operations(setup_test_environment):
    """Test that filesystem operations work correctly with real files."""
    env = setup_test_environment
    
    # Copy test email
    fixture_email = os.path.join(
        os.path.dirname(__file__),
        "fixtures",
        "emails",
        "sample_single_joke.eml"
    )
    test_email = os.path.join(
        env['pipeline_main'],
        "01_parse",
        "fs_test.eml"
    )
    shutil.copy(fixture_email, test_email)
    
    # Verify email exists before processing
    assert os.path.exists(test_email)
    
    # Create processor and run
    processor = ParseProcessor()
    processor.run()
    
    # Verify email was deleted
    assert not os.path.exists(test_email)
    
    # Verify joke file exists
    parsed_dir = os.path.join(env['pipeline_main'], "02_dedup")
    joke_files = [f for f in os.listdir(parsed_dir) if f.endswith('.txt')]
    assert len(joke_files) == 1
    
    # Verify file is readable
    joke_path = os.path.join(parsed_dir, joke_files[0])
    assert os.path.isfile(joke_path)
    headers, content = parse_joke_file(joke_path)
    assert len(content) > 0


def test_preserves_title_and_submitter(setup_test_environment):
    """Test that Title and Submitter from joke-extract.py are preserved."""
    env = setup_test_environment
    
    # Copy test email - use filename that mock_joke_extract.py recognizes
    fixture_email = os.path.join(
        os.path.dirname(__file__),
        "fixtures",
        "emails",
        "sample_single_joke.eml"
    )
    test_email = os.path.join(
        env['pipeline_main'],
        "01_parse",
        "preserve_single_joke_test.eml"  # Include 'single_joke' for mock to recognize
    )
    shutil.copy(fixture_email, test_email)
    
    # Create processor and run
    processor = ParseProcessor()
    processor.run()
    
    # Get joke file
    parsed_dir = os.path.join(env['pipeline_main'], "02_dedup")
    joke_files = [f for f in os.listdir(parsed_dir) if f.endswith('.txt')]
    joke_path = os.path.join(parsed_dir, joke_files[0])
    
    # Parse joke
    headers, content = parse_joke_file(joke_path)
    
    # Verify Title preserved
    assert 'Title' in headers
    assert headers['Title'] == 'Colorful Meal'
    
    # Verify Submitter preserved
    assert 'Submitter' in headers
    assert 'Thomas S. Ellsworth' in headers['Submitter']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
