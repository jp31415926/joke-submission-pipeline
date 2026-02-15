#!/usr/bin/env python3
"""
Tests for file_utils module
"""

import os
import tempfile
import unittest
from unittest.mock import patch

# Add the project root to the path so we can import file_utils
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from file_utils import parse_joke_file, write_joke_file, validate_headers, atomic_write, atomic_move, safe_cleanup, generate_joke_id, initialize_metadata


class TestFileUtils(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_parse_joke_extract_format(self):
        """Test parsing joke-extract.py format (Title and Submitter only)"""
        sample_content = """Title: Colorful Meal
Submitter: "'Thomas S. Ellsworth' tellswor@kcbx.net [good-clean-fun]" <good-clean-fun-noreply@yahoogroups.com>

Over dinner, I explained the health benefits of a colorful meal to my family. "The more colors, the more variety of nutrients," I told them. Pointing to our food, I asked, "How many different colors do you see?"

"Six," volunteered my daughter. "Seven if you count the burned parts."
"""
        test_file = os.path.join(self.test_dir, "test_extract.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        
        headers, content = parse_joke_file(test_file)
        
        self.assertEqual(headers['Title'], "Colorful Meal")
        self.assertEqual(headers['Submitter'], "'Thomas S. Ellsworth' tellswor@kcbx.net [good-clean-fun] <good-clean-fun-noreply@yahoogroups.com>")
        self.assertEqual(content.strip(), """Over dinner, I explained the health benefits of a colorful meal to my family. "The more colors, the more variety of nutrients," I told them. Pointing to our food, I asked, "How many different colors do you see?"

"Six," volunteered my daughter. "Seven if you count the burned parts." """)
    
    def test_parse_full_pipeline_format(self):
        """Test parsing full pipeline format (all headers)"""
        sample_content = """Joke-ID: 550e8400-e29b-41d4-a716-446655440000
Title: Why the Chicken Crossed the Road
Submitter: "John Doe" <john@example.com>
Source-Email-File: 1700000000.M1234.mailbox
Pipeline-Stage: 07_titled
Duplicate-Score: 42
Duplicate-Threshold: 70
Cleanliness-Status: PASS
Cleanliness-Confidence: 85
Format-Status: PASS
Format-Confidence: 92
Categories: Animals, Wordplay
Category-Confidence: 77
Rejection-Reason:

Why did the chicken cross the road?
To get to the other side!
"""
        test_file = os.path.join(self.test_dir, "test_full.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        
        headers, content = parse_joke_file(test_file)
        
        self.assertEqual(headers['Joke-ID'], "550e8400-e29b-41d4-a716-446655440000")
        self.assertEqual(headers['Title'], "Why the Chicken Crossed the Road")
        self.assertEqual(headers['Submitter'], '"John Doe" <john@example.com>')
        self.assertEqual(headers['Source-Email-File'], "1700000000.M1234.mailbox")
        self.assertEqual(headers['Pipeline-Stage'], "07_titled")
        self.assertEqual(headers['Duplicate-Score'], "42")
        self.assertEqual(headers['Duplicate-Threshold'], "70")
        self.assertEqual(headers['Cleanliness-Status'], "PASS")
        self.assertEqual(headers['Cleanliness-Confidence'], "85")
        self.assertEqual(headers['Format-Status'], "PASS")
        self.assertEqual(headers['Format-Confidence'], "92")
        self.assertEqual(headers['Categories'], "Animals, Wordplay")
        self.assertEqual(headers['Category-Confidence'], "77")
        self.assertEqual(headers['Rejection-Reason'], "")
        self.assertEqual(content.strip(), """Why did the chicken cross the road?
To get to the other side!""")
    
    def test_parse_file_with_blank_title(self):
        """Test parsing file with blank Title field"""
        sample_content = """Title: 
Submitter: "John Doe" <john@example.com>

This is a joke with blank title.
"""
        test_file = os.path.join(self.test_dir, "test_blank_title.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        
        headers, content = parse_joke_file(test_file)
        
        self.assertEqual(headers['Title'], "")
        self.assertEqual(headers['Submitter'], '"John Doe" <john@example.com>')
        self.assertEqual(content.strip(), "This is a joke with blank title.")
    
    def test_round_trip_write_read(self):
        """Test that write then read produces identical data"""
        original_headers = {
            "Joke-ID": "550e8400-e29b-41d4-a716-446655440000",
            "Title": "Why the Chicken Crossed the Road",
            "Submitter": '"John Doe" <john@example.com>',
            "Source-Email-File": "1700000000.M1234.mailbox",
            "Pipeline-Stage": "07_titled"
        }
        original_content = "Why did the chicken cross the road?\nTo get to the other side!\n"
        
        test_file = os.path.join(self.test_dir, "test_round_trip.txt")
        write_joke_file(test_file, original_headers, original_content)
        
        headers, content = parse_joke_file(test_file)
        
        self.assertEqual(headers, original_headers)
        self.assertEqual(content.strip(), original_content.strip())
    
    def test_validate_headers_all_present(self):
        """Test validation with all required fields present"""
        headers = {
            "Joke-ID": "550e8400-e29b-41d4-a716-446655440000",
            "Title": "Why the Chicken Crossed the Road",
            "Submitter": '"John Doe" <john@example.com>',
            "Source-Email-File": "1700000000.M1234.mailbox",
            "Pipeline-Stage": "07_titled"
        }
        required_fields = ["Joke-ID", "Title", "Submitter", "Source-Email-File", "Pipeline-Stage"]
        
        is_valid, missing_fields = validate_headers(headers, required_fields)
        self.assertTrue(is_valid)
        self.assertEqual(missing_fields, [])
        
    def test_validate_headers_missing_fields(self):
        """Test validation with missing required fields"""
        headers = {
            "Joke-ID": "550e8400-e29b-41d4-a716-446655440000",
            "Title": "Why the Chicken Crossed the Road",
            # Missing Submitter, Source-Email-File, Pipeline-Stage
        }
        required_fields = ["Joke-ID", "Title", "Submitter", "Source-Email-File", "Pipeline-Stage"]
        
        is_valid, missing_fields = validate_headers(headers, required_fields)
        self.assertFalse(is_valid)
        self.assertEqual(set(missing_fields), {"Submitter", "Source-Email-File", "Pipeline-Stage"})
        
    def test_validate_headers_empty_string_values(self):
        """Test validation with empty string values"""
        headers = {
            "Joke-ID": "550e8400-e29b-41d4-a716-446655440000",
            "Title": "",  # Empty string
            "Submitter": '"John Doe" <john@example.com>',
        }
        required_fields = ["Joke-ID", "Title", "Submitter"]
        
        is_valid, missing_fields = validate_headers(headers, required_fields)
        self.assertFalse(is_valid)
        self.assertEqual(missing_fields, ["Title"])
        
    def test_parse_no_headers(self):
        """Test parsing file with no headers (joke-extract.py format)"""
        sample_content = """Over dinner, I explained the health benefits of a colorful meal to my family. "The more colors, the more variety of nutrients," I told them. Pointing to our food, I asked, "How many different colors do you see?"

"Six," volunteered my daughter. "Seven if you count the burned parts."
"""
        test_file = os.path.join(self.test_dir, "test_no_headers.txt")
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(sample_content)
        
        headers, content = parse_joke_file(test_file)
        
        self.assertEqual(headers, {})
        self.assertEqual(content.strip(), """Over dinner, I explained the health benefits of a colorful meal to my family. "The more colors, the more variety of nutrients," I told them. Pointing to our food, I asked, "How many different colors do you see?"

"Six," volunteered my daughter. "Seven if you count the burned parts." """)
    
    def test_atomic_write(self):
        """Test atomic_write creates file in tmp/ first and moves to final destination"""
        test_headers = {
            "Joke-ID": "550e8400-e29b-41d4-a716-446655440000",
            "Title": "Why the Chicken Crossed the Road",
            "Submitter": '"John Doe" <john@example.com>',
        }
        test_content = "Why did the chicken cross the road?\nTo get to the other side!\n"
        target_path = os.path.join(self.test_dir, "test_atomic_write.txt")
        
        # Test the atomic write function
        result = atomic_write(target_path, test_headers, test_content)
        
        # Should return True on success
        self.assertTrue(result)
        
        # Verify the file exists at the target location
        self.assertTrue(os.path.exists(target_path))
        
        # Verify the file contains what we expect
        headers, content = parse_joke_file(target_path)
        self.assertEqual(headers["Joke-ID"], "550e8400-e29b-41d4-a716-446655440000")
        self.assertEqual(content.strip(), test_content.strip())
        
        # Verify there are no temporary files left in tmp directory
        tmp_dir = os.path.join(self.test_dir, "tmp")
        if os.path.exists(tmp_dir):
            self.assertEqual(len(os.listdir(tmp_dir)), 0)
    
    def test_atomic_move(self):
        """Test atomic_move uses tmp/ subdirectory and deletes source after successful move"""
        # Create source file
        source_headers = {
            "Joke-ID": "550e8400-e29b-41d4-a716-446655440000",
            "Title": "Why the Chicken Crossed the Road",
            "Submitter": '"John Doe" <john@example.com>',
        }
        source_content = "Why did the chicken cross the road?\nTo get to the other side!\n"
        source_file = os.path.join(self.test_dir, "source_file.txt")
        write_joke_file(source_file, source_headers, source_content)
        
        # Create destination directory
        dest_dir = os.path.join(self.test_dir, "dest_dir")
        
        # Test the atomic move function
        result = atomic_move(source_file, dest_dir)
        
        # Should return destination path on success
        expected_dest = os.path.join(dest_dir, "source_file.txt")
        self.assertEqual(result, expected_dest)
        
        # Verify source file is deleted
        self.assertFalse(os.path.exists(source_file))
        
        # Verify destination file exists
        self.assertTrue(os.path.exists(expected_dest))
        
        # Verify destination file contains what we expect
        headers, content = parse_joke_file(expected_dest)
        self.assertEqual(headers["Joke-ID"], "550e8400-e29b-41d4-a716-446655440000")
        self.assertEqual(content.strip(), source_content.strip())
        
        # Verify there are no temporary files left in tmp directory
        tmp_dir = os.path.join(dest_dir, "tmp")
        if os.path.exists(tmp_dir):
            self.assertEqual(len(os.listdir(tmp_dir)), 0)
    
    def test_safe_cleanup_existing_file(self):
        """Test safe_cleanup removes existing file"""
        # Create a test file
        test_file = os.path.join(self.test_dir, "test_file_to_delete.txt")
        with open(test_file, 'w') as f:
            f.write("test content")
        
        # Verify file exists
        self.assertTrue(os.path.exists(test_file))
        
        # Test safe_cleanup
        safe_cleanup(test_file)
        
        # Verify file is deleted
        self.assertFalse(os.path.exists(test_file))
        
    def test_safe_cleanup_nonexistent_file(self):
        """Test safe_cleanup handles non-existent file gracefully"""
        # Try to clean up a file that doesn't exist
        nonexistent_file = os.path.join(self.test_dir, "does_not_exist.txt")
        
        # This should not raise an exception
        try:
            safe_cleanup(nonexistent_file)
        except Exception as e:
            self.fail(f"safe_cleanup raised exception on non-existent file: {e}")
    
    def test_generate_joke_id_returns_valid_uuid(self):
        """Test generate_joke_id returns valid UUID format"""
        import re
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
        
        joke_id = generate_joke_id()
        
        # Verify it's a string
        self.assertIsInstance(joke_id, str)
        
        # Verify it matches UUID format
        self.assertIsNotNone(uuid_pattern.match(joke_id))
    
    def test_generate_joke_id_creates_unique_ids(self):
        """Test generate_joke_id creates unique IDs (generate 100, verify all unique)"""
        joke_ids = [generate_joke_id() for _ in range(100)]
        
        # Verify all are unique
        self.assertEqual(len(joke_ids), len(set(joke_ids)))
    
    def test_initialize_metadata_adds_joke_id(self):
        """Test initialize_metadata adds Joke-ID"""
        headers = {
            "Title": "Test Joke",
            "Submitter": "test@example.com"
        }
        
        updated_headers = initialize_metadata(headers, "test_email.txt", "01_extracted")
        
        # Verify Joke-ID was added
        self.assertIn("Joke-ID", updated_headers)
        
        # Verify it's a valid UUID format
        import re
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$')
        self.assertIsNotNone(uuid_pattern.match(updated_headers["Joke-ID"]))
    
    def test_initialize_metadata_adds_source_email_file(self):
        """Test initialize_metadata adds Source-Email-File"""
        headers = {
            "Title": "Test Joke",
            "Submitter": "test@example.com"
        }
        
        updated_headers = initialize_metadata(headers, "test_email.txt", "01_extracted")
        
        # Verify Source-Email-File was added
        self.assertIn("Source-Email-File", updated_headers)
        self.assertEqual(updated_headers["Source-Email-File"], "test_email.txt")
    
    def test_initialize_metadata_adds_pipeline_stage(self):
        """Test initialize_metadata adds Pipeline-Stage"""
        headers = {
            "Title": "Test Joke",
            "Submitter": "test@example.com"
        }
        
        updated_headers = initialize_metadata(headers, "test_email.txt", "01_extracted")
        
        # Verify Pipeline-Stage was added
        self.assertIn("Pipeline-Stage", updated_headers)
        self.assertEqual(updated_headers["Pipeline-Stage"], "01_extracted")
    
    def test_initialize_metadata_preserves_existing_headers(self):
        """Test initialize_metadata preserves existing headers (Title, Submitter)"""
        headers = {
            "Title": "Test Joke",
            "Submitter": "test@example.com"
        }
        
        updated_headers = initialize_metadata(headers, "test_email.txt", "01_extracted")
        
        # Verify existing headers are preserved
        self.assertEqual(updated_headers["Title"], "Test Joke")
        self.assertEqual(updated_headers["Submitter"], "test@example.com")
    
    def test_initialize_metadata_doesnt_overwrite_existing_joke_id(self):
        """Test initialize_metadata doesn't overwrite existing Joke-ID"""
        existing_joke_id = "550e8400-e29b-41d4-a716-446655440000"
        headers = {
            "Joke-ID": existing_joke_id,
            "Title": "Test Joke",
            "Submitter": "test@example.com"
        }
        
        updated_headers = initialize_metadata(headers, "test_email.txt", "01_extracted")
        
        # Verify existing Joke-ID is not overwritten
        self.assertEqual(updated_headers["Joke-ID"], existing_joke_id)


if __name__ == '__main__':
    unittest.main()