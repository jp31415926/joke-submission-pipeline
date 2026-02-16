#!/usr/bin/env python3
"""
Simple test runner for stage_incoming tests (without pytest dependency).
"""

import os
import sys
import shutil
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stage_incoming import IncomingProcessor
from file_utils import parse_joke_file
import config


class SimpleTestRunner:
    """Simple test runner (named to avoid pytest collection)."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.test_dir = None
        self.pipeline_main = None
        self.pipeline_priority = None
        self.orig_pipeline_main = None
        self.orig_pipeline_priority = None
        self.orig_joke_extractor = None
    
    def setup(self):
        """Setup test environment."""
        # Create temporary directories for testing
        self.test_dir = tempfile.mkdtemp(prefix="test_incoming_")
        self.pipeline_main = os.path.join(self.test_dir, "pipeline-main")
        self.pipeline_priority = os.path.join(self.test_dir, "pipeline-priority")
        
        # Create directory structure
        os.makedirs(os.path.join(self.pipeline_main, "01_incoming"))
        os.makedirs(os.path.join(self.pipeline_main, "02_parsed"))
        os.makedirs(os.path.join(self.pipeline_main, "50_rejected_parse"))
        os.makedirs(os.path.join(self.pipeline_priority, "01_incoming"))
        os.makedirs(os.path.join(self.pipeline_priority, "02_parsed"))
        os.makedirs(os.path.join(self.pipeline_priority, "50_rejected_parse"))
        
        # Store original config values
        self.orig_pipeline_main = config.PIPELINE_MAIN
        self.orig_pipeline_priority = config.PIPELINE_PRIORITY
        self.orig_joke_extractor = config.JOKE_EXTRACTOR
        
        # Update config to use test directories
        config.PIPELINE_MAIN = self.pipeline_main
        config.PIPELINE_PRIORITY = self.pipeline_priority
        
        # Use mock joke-extract.py
        mock_script = os.path.join(
            os.path.dirname(__file__),
            "fixtures",
            "mock_joke_extract.py"
        )
        config.JOKE_EXTRACTOR = mock_script
    
    def teardown(self):
        """Teardown test environment."""
        # Restore original config
        config.PIPELINE_MAIN = self.orig_pipeline_main
        config.PIPELINE_PRIORITY = self.orig_pipeline_priority
        config.JOKE_EXTRACTOR = self.orig_joke_extractor
        
        # Clean up test directory
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
    
    def run_test(self, test_name, test_func):
        """Run a single test."""
        try:
            self.setup()
            test_func()
            print(f"✓ {test_name}")
            self.passed += 1
        except AssertionError as e:
            print(f"✗ {test_name}: {e}")
            self.failed += 1
        except Exception as e:
            print(f"✗ {test_name}: ERROR - {e}")
            self.failed += 1
        finally:
            self.teardown()
    
    def test_process_single_joke_email(self):
        """Test processing an email with a single joke."""
        # Copy test email to incoming directory
        fixture_email = os.path.join(
            os.path.dirname(__file__),
            "fixtures",
            "emails",
            "sample_single_joke.eml"
        )
        test_email = os.path.join(
            self.pipeline_main,
            "01_incoming",
            "sample_single_joke.eml"
        )
        shutil.copy(fixture_email, test_email)
        
        # Create processor and run
        processor = IncomingProcessor()
        processor.run()
        
        # Verify email was deleted from incoming
        assert not os.path.exists(test_email), "Email should be deleted from incoming"
        
        # Verify joke file was created in parsed directory
        parsed_dir = os.path.join(self.pipeline_main, "02_parsed")
        joke_files = [f for f in os.listdir(parsed_dir) if f.endswith('.txt')]
        assert len(joke_files) == 1, f"Expected 1 joke file, got {len(joke_files)}"
        
        # Parse the joke file
        joke_path = os.path.join(parsed_dir, joke_files[0])
        headers, content = parse_joke_file(joke_path)
        
        # Verify headers
        assert 'Joke-ID' in headers, "Joke-ID header missing"
        assert 'Source-Email-File' in headers, "Source-Email-File header missing"
        assert headers['Source-Email-File'] == 'sample_single_joke.eml', "Wrong source email file"
        assert headers['Pipeline-Stage'] == '02_parsed', "Wrong pipeline stage"
        assert headers['Title'] == 'Colorful Meal', "Wrong title"
        assert 'Submitter' in headers, "Submitter header missing"
        
        # Verify content
        assert 'colorful meal' in content.lower(), "Content missing expected text"
        assert 'burned parts' in content.lower(), "Content missing expected text"
    
    def test_process_multiple_jokes_email(self):
        """Test processing an email with multiple jokes."""
        # Copy test email to incoming directory
        fixture_email = os.path.join(
            os.path.dirname(__file__),
            "fixtures",
            "emails",
            "sample_multiple_jokes.eml"
        )
        test_email = os.path.join(
            self.pipeline_main,
            "01_incoming",
            "sample_multiple_jokes.eml"
        )
        shutil.copy(fixture_email, test_email)
        
        # Create processor and run
        processor = IncomingProcessor()
        processor.run()
        
        # Verify email was deleted from incoming
        assert not os.path.exists(test_email), "Email should be deleted"
        
        # Verify two joke files were created in parsed directory
        parsed_dir = os.path.join(self.pipeline_main, "02_parsed")
        joke_files = [f for f in os.listdir(parsed_dir) if f.endswith('.txt')]
        assert len(joke_files) == 2, f"Expected 2 joke files, got {len(joke_files)}"
        
        # Verify each joke has unique UUID
        joke_ids = []
        for joke_file in joke_files:
            joke_path = os.path.join(parsed_dir, joke_file)
            headers, content = parse_joke_file(joke_path)
            
            # Verify headers
            assert 'Joke-ID' in headers, "Joke-ID missing"
            assert headers['Source-Email-File'] == 'sample_multiple_jokes.eml'
            assert headers['Pipeline-Stage'] == '02_parsed'
            
            joke_ids.append(headers['Joke-ID'])
        
        # Verify UUIDs are unique
        assert len(set(joke_ids)) == 2, "Joke IDs are not unique"
    
    def test_process_no_jokes_email(self):
        """Test processing an email with no jokes (should reject)."""
        # Copy test email to incoming directory
        fixture_email = os.path.join(
            os.path.dirname(__file__),
            "fixtures",
            "emails",
            "sample_no_jokes.eml"
        )
        test_email = os.path.join(
            self.pipeline_main,
            "01_incoming",
            "sample_no_jokes.eml"
        )
        shutil.copy(fixture_email, test_email)
        
        # Create processor and run
        processor = IncomingProcessor()
        processor.run()
        
        # Verify email was moved to reject directory
        assert not os.path.exists(test_email), "Email should not be in incoming"
        
        # Verify no jokes in parsed directory
        parsed_dir = os.path.join(self.pipeline_main, "02_parsed")
        joke_files = [f for f in os.listdir(parsed_dir) if f.endswith('.txt')]
        assert len(joke_files) == 0, f"Expected 0 jokes, got {len(joke_files)}"
        
        # Verify email in reject directory
        reject_dir = os.path.join(self.pipeline_main, "50_rejected_parse")
        reject_files = [f for f in os.listdir(reject_dir) if f.endswith('.eml')]
        assert len(reject_files) == 1, f"Expected 1 rejected email, got {len(reject_files)}"
    
    def test_uuid_generation(self):
        """Test that each joke gets a unique UUID."""
        # Copy test email with multiple jokes
        fixture_email = os.path.join(
            os.path.dirname(__file__),
            "fixtures",
            "emails",
            "sample_multiple_jokes.eml"
        )
        test_email = os.path.join(
            self.pipeline_main,
            "01_incoming",
            "sample_multiple_jokes.eml"
        )
        shutil.copy(fixture_email, test_email)
        
        # Create processor and run
        processor = IncomingProcessor()
        processor.run()
        
        # Get all joke files
        parsed_dir = os.path.join(self.pipeline_main, "02_parsed")
        joke_files = [f for f in os.listdir(parsed_dir) if f.endswith('.txt')]
        
        # Verify each file has a UUID filename
        import re
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
            assert headers['Joke-ID'] == expected_id, "Joke-ID doesn't match filename"
    
    def test_metadata_initialization(self):
        """Test that metadata is properly initialized for each joke."""
        # Copy test email
        fixture_email = os.path.join(
            os.path.dirname(__file__),
            "fixtures",
            "emails",
            "sample_single_joke.eml"
        )
        test_email = os.path.join(
            self.pipeline_main,
            "01_incoming",
            "test_metadata.eml"
        )
        shutil.copy(fixture_email, test_email)
        
        # Create processor and run
        processor = IncomingProcessor()
        processor.run()
        
        # Get joke file
        parsed_dir = os.path.join(self.pipeline_main, "02_parsed")
        joke_files = [f for f in os.listdir(parsed_dir) if f.endswith('.txt')]
        assert len(joke_files) == 1
        
        # Parse joke
        joke_path = os.path.join(parsed_dir, joke_files[0])
        headers, content = parse_joke_file(joke_path)
        
        # Verify required metadata fields
        assert 'Joke-ID' in headers, "Joke-ID missing"
        assert 'Source-Email-File' in headers, "Source-Email-File missing"
        assert 'Pipeline-Stage' in headers, "Pipeline-Stage missing"
        
        # Verify values
        assert headers['Source-Email-File'] == 'test_metadata.eml'
        assert headers['Pipeline-Stage'] == '02_parsed'
        
        # Verify original headers preserved
        assert 'Title' in headers
        assert 'Submitter' in headers


def main():
    """Run all tests."""
    runner = SimpleTestRunner()
    
    print("Running Stage Incoming Tests")
    print("=" * 60)
    
    runner.run_test("test_process_single_joke_email", runner.test_process_single_joke_email)
    runner.run_test("test_process_multiple_jokes_email", runner.test_process_multiple_jokes_email)
    runner.run_test("test_process_no_jokes_email", runner.test_process_no_jokes_email)
    runner.run_test("test_uuid_generation", runner.test_uuid_generation)
    runner.run_test("test_metadata_initialization", runner.test_metadata_initialization)
    
    print("=" * 60)
    print(f"Results: {runner.passed} passed, {runner.failed} failed")
    
    return 0 if runner.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
