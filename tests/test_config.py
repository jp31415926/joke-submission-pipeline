#!/usr/bin/env python3
"""
Test cases for config.py
"""

import sys
import os
import pytest

# Add the current directory to sys.path to import config
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/..")

import config

def test_config_imports_successfully():
    """Test that config.py imports without errors."""
    assert config is not None

def test_required_constants_present():
    """Test that all required constants are present."""
    # Directory paths
    assert hasattr(config, 'PIPELINE_MAIN')
    assert hasattr(config, 'PIPELINE_PRIORITY')
    
    # STAGES dictionary
    assert hasattr(config, 'STAGES')
    assert isinstance(config.STAGES, dict)
    assert 'incoming' in config.STAGES
    assert 'parsed' in config.STAGES
    assert 'deduped' in config.STAGES
    assert 'clean_checked' in config.STAGES
    assert 'formatted' in config.STAGES
    assert 'categorized' in config.STAGES
    assert 'titled' in config.STAGES
    assert 'ready_for_review' in config.STAGES
    
    # REJECTS dictionary
    assert hasattr(config, 'REJECTS')
    assert isinstance(config.REJECTS, dict)
    assert 'parse' in config.REJECTS
    assert 'duplicate' in config.REJECTS
    assert 'cleanliness' in config.REJECTS
    assert 'format' in config.REJECTS
    assert 'category' in config.REJECTS
    assert 'titled' in config.REJECTS
    
    # Script paths
    assert hasattr(config, 'JOKE_EXTRACTOR')
    assert hasattr(config, 'BUILD_TFIDF')
    assert hasattr(config, 'SEARCH_TFIDF')
    
    # Thresholds
    assert hasattr(config, 'DUPLICATE_THRESHOLD')
    assert hasattr(config, 'CLEANLINESS_MIN_CONFIDENCE')
    assert hasattr(config, 'CATEGORIZATION_MIN_CONFIDENCE')
    
    # Ollama config
    assert hasattr(config, 'ollama_config')
    assert isinstance(config.ollama_config, dict)
    
    # Categories
    assert hasattr(config, 'VALID_CATEGORIES')
    assert isinstance(config.VALID_CATEGORIES, list)
    assert len(config.VALID_CATEGORIES) > 0
    
    assert hasattr(config, 'MAX_CATEGORIES_PER_JOKE')
    
    # Logging
    assert hasattr(config, 'LOG_DIR')
    assert hasattr(config, 'LOG_LEVEL')
    
    # Error Handling
    assert hasattr(config, 'MAX_RETRIES')

def test_data_types():
    """Test that configuration values have correct data types."""
    # Thresholds should be integers
    assert isinstance(config.DUPLICATE_THRESHOLD, int)
    assert isinstance(config.CLEANLINESS_MIN_CONFIDENCE, int)
    assert isinstance(config.CATEGORIZATION_MIN_CONFIDENCE, int)
    
    # MAX_RETRIES should be an integer
    assert isinstance(config.MAX_RETRIES, int)
    
    # MAX_CATEGORIES_PER_JOKE should be an integer
    assert isinstance(config.MAX_CATEGORIES_PER_JOKE, int)
    
    # LOG_LEVEL should be a string
    assert isinstance(config.LOG_LEVEL, str)
    
    # Ollama config should be a dictionary with required keys
    assert 'ollama_api_url' in config.ollama_config
    assert 'ollama_model' in config.ollama_config
    assert 'ollama_prefix_prompt' in config.ollama_config
    assert 'ollama_think' in config.ollama_config
    assert 'ollama_keep_alive' in config.ollama_config
    assert 'ollama_options' in config.ollama_config
    assert isinstance(config.ollama_config['ollama_options'], dict)

def test_valid_categories():
    """Test that VALID_CATEGORIES is a non-empty list."""
    assert isinstance(config.VALID_CATEGORIES, list)
    assert len(config.VALID_CATEGORIES) > 0

def test_ollama_config_has_required_keys():
    """Test that ollama_config has all required keys."""
    required_keys = [
        'ollama_api_url',
        'ollama_model', 
        'ollama_prefix_prompt',
        'ollama_think',
        'ollama_keep_alive',
        'ollama_options'
    ]
    
    for key in required_keys:
        assert key in config.ollama_config, f"Missing key in ollama_config: {key}"
    
    assert 'temperature' in config.ollama_config['ollama_options']
    assert 'num_ctx' in config.ollama_config['ollama_options']
    assert 'repeat_penalty' in config.ollama_config['ollama_options']
    assert 'top_k' in config.ollama_config['ollama_options']
    assert 'top_p' in config.ollama_config['ollama_options']
    assert 'min_p' in config.ollama_config['ollama_options']
    assert 'repeat_last_n' in config.ollama_config['ollama_options']

def test_pipeline_paths_exist():
    """Test that pipeline paths are properly set."""
    # Check that paths are strings
    assert isinstance(config.PIPELINE_MAIN, str)
    assert isinstance(config.PIPELINE_PRIORITY, str)
    assert len(config.PIPELINE_MAIN) > 0
    assert len(config.PIPELINE_PRIORITY) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])