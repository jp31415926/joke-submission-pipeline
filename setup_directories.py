#!/usr/bin/env python3
"""
Setup script to create all required directories for the joke submission pipeline.
"""

import os
import sys
from pathlib import Path

# Add the current directory to sys.path to import config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config

def setup_directories():
    """
    Create all required pipeline directories for both main and priority pipelines.
    
    This function creates all stage directories, tmp/ subdirectories,
    and the log directory specified in config.py.
    
    Returns:
        bool: True if all directories were created successfully, False otherwise.
    """
    try:
        # Create main pipeline directories
        main_pipeline_path = Path(config.PIPELINE_MAIN)
        main_pipeline_path.mkdir(parents=True, exist_ok=True)
        
        # Create stage directories in main pipeline
        for stage_name, stage_dir in config.STAGES.items():
            stage_path = main_pipeline_path / stage_dir
            stage_path.mkdir(parents=True, exist_ok=True)
            tmp_path = stage_path / "tmp"
            tmp_path.mkdir(parents=True, exist_ok=True)
        
        # Create reject directories in main pipeline
        for reject_name, reject_dir in config.REJECTS.items():
            reject_path = main_pipeline_path / reject_dir
            reject_path.mkdir(parents=True, exist_ok=True)
        
        # Create priority pipeline directories
        priority_pipeline_path = Path(config.PIPELINE_PRIORITY)
        priority_pipeline_path.mkdir(parents=True, exist_ok=True)
        
        # Create stage directories in priority pipeline
        for stage_name, stage_dir in config.STAGES.items():
            stage_path = priority_pipeline_path / stage_dir
            stage_path.mkdir(parents=True, exist_ok=True)
            tmp_path = stage_path / "tmp"
            tmp_path.mkdir(parents=True, exist_ok=True)
        
        # Create reject directories in priority pipeline
        for reject_name, reject_dir in config.REJECTS.items():
            reject_path = priority_pipeline_path / reject_dir
            reject_path.mkdir(parents=True, exist_ok=True)
        
        # Create log directory
        log_path = Path(config.LOG_DIR)
        log_path.mkdir(parents=True, exist_ok=True)
        
        print("All pipeline directories created successfully.")
        return True
        
    except Exception as e:
        print(f"Error creating directories: {e}")
        return False

if __name__ == "__main__":
    success = setup_directories()
    sys.exit(0 if success else 1)