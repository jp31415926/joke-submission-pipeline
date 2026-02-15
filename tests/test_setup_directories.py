#!/usr/bin/env python3
"""
Test cases for setup_directories.py
"""

import os
import sys
import tempfile
import shutil
import pytest
from pathlib import Path

# Add the current directory to sys.path to import config and setup_directories
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

import config
from setup_directories import setup_directories

def test_setup_directories_creates_all_directories():
    """Test that setup_directories creates all required directories."""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Modify config to use temp directory
        original_main = config.PIPELINE_MAIN
        original_priority = config.PIPELINE_PRIORITY
        original_log = config.LOG_DIR
        
        try:
            config.PIPELINE_MAIN = os.path.join(temp_dir, "pipeline-main")
            config.PIPELINE_PRIORITY = os.path.join(temp_dir, "pipeline-priority")
            config.LOG_DIR = os.path.join(temp_dir, "logs")
            
            # Run setup
            success = setup_directories()
            
            assert success, "setup_directories should return True on success"
            
            # Verify main pipeline directories were created
            main_path = Path(config.PIPELINE_MAIN)
            assert main_path.exists(), "Main pipeline directory should exist"
            
            # Check all stage directories in main pipeline
            for stage_name, stage_dir in config.STAGES.items():
                stage_path = main_path / stage_dir
                assert stage_path.exists(), f"Stage directory {stage_dir} should exist in main pipeline"
                tmp_path = stage_path / "tmp"
                assert tmp_path.exists(), f"tmp directory should exist in {stage_dir}"
            
            # Check all reject directories in main pipeline
            for reject_name, reject_dir in config.REJECTS.items():
                reject_path = main_path / reject_dir
                assert reject_path.exists(), f"Reject directory {reject_dir} should exist in main pipeline"
            
            # Verify priority pipeline directories were created
            priority_path = Path(config.PIPELINE_PRIORITY)
            assert priority_path.exists(), "Priority pipeline directory should exist"
            
            # Check all stage directories in priority pipeline
            for stage_name, stage_dir in config.STAGES.items():
                stage_path = priority_path / stage_dir
                assert stage_path.exists(), f"Stage directory {stage_dir} should exist in priority pipeline"
                tmp_path = stage_path / "tmp"
                assert tmp_path.exists(), f"tmp directory should exist in {stage_dir}"
            
            # Check all reject directories in priority pipeline
            for reject_name, reject_dir in config.REJECTS.items():
                reject_path = priority_path / reject_dir
                assert reject_path.exists(), f"Reject directory {reject_dir} should exist in priority pipeline"
            
            # Verify log directory was created
            log_path = Path(config.LOG_DIR)
            assert log_path.exists(), "Log directory should exist"
            
        finally:
            # Restore original config values
            config.PIPELINE_MAIN = original_main
            config.PIPELINE_PRIORITY = original_priority
            config.LOG_DIR = original_log

def test_setup_directories_idempotent():
    """Test that setup_directories can be run multiple times without errors."""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Modify config to use temp directory
        original_main = config.PIPELINE_MAIN
        original_priority = config.PIPELINE_PRIORITY
        original_log = config.LOG_DIR
        
        try:
            config.PIPELINE_MAIN = os.path.join(temp_dir, "pipeline-main")
            config.PIPELINE_PRIORITY = os.path.join(temp_dir, "pipeline-priority")
            config.LOG_DIR = os.path.join(temp_dir, "logs")
            
            # Run setup twice
            success1 = setup_directories()
            success2 = setup_directories()
            
            assert success1, "First setup_directories should return True"
            assert success2, "Second setup_directories should return True"
            
        finally:
            # Restore original config values
            config.PIPELINE_MAIN = original_main
            config.PIPELINE_PRIORITY = original_priority
            config.LOG_DIR = original_log

def test_setup_directories_with_existing_directories():
    """Test that setup_directories handles existing directories gracefully."""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create some directories beforehand
        existing_main = os.path.join(temp_dir, "pipeline-main")
        existing_priority = os.path.join(temp_dir, "pipeline-priority")
        existing_log = os.path.join(temp_dir, "logs")
        
        os.makedirs(existing_main, exist_ok=True)
        os.makedirs(existing_priority, exist_ok=True)
        os.makedirs(existing_log, exist_ok=True)
        
        # Modify config to use temp directory
        original_main = config.PIPELINE_MAIN
        original_priority = config.PIPELINE_PRIORITY
        original_log = config.LOG_DIR
        
        try:
            config.PIPELINE_MAIN = existing_main
            config.PIPELINE_PRIORITY = existing_priority
            config.LOG_DIR = existing_log
            
            # Run setup - should not fail with existing directories
            success = setup_directories()
            
            assert success, "setup_directories should handle existing directories gracefully"
            
        finally:
            # Restore original config values
            config.PIPELINE_MAIN = original_main
            config.PIPELINE_PRIORITY = original_priority
            config.LOG_DIR = original_log

if __name__ == "__main__":
    pytest.main([__file__, "-v"])