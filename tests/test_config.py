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
import joke_categories

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
    assert 'parse' in config.STAGES
    assert 'dedup' in config.STAGES
    assert 'clean_check' in config.STAGES
    assert 'format' in config.STAGES
    assert 'categorize' in config.STAGES
    assert 'title' in config.STAGES
    assert 'ready_for_review' in config.STAGES

    # REJECTS dictionary
    assert hasattr(config, 'REJECTS')
    assert isinstance(config.REJECTS, dict)
    assert 'parse' in config.REJECTS
    assert 'dedup' in config.REJECTS
    assert 'clean_check' in config.REJECTS
    assert 'format' in config.REJECTS
    assert 'categorize' in config.REJECTS
    assert 'title' in config.REJECTS
    
    # Script paths
    assert hasattr(config, 'JOKE_EXTRACTOR')
    assert hasattr(config, 'BUILD_TFIDF')
    assert hasattr(config, 'SEARCH_TFIDF')
    
    # Timeouts
    assert hasattr(config, 'EXTERNAL_SCRIPT_TIMEOUT')
    assert hasattr(config, 'OLLAMA_TIMEOUT')

    # Thresholds
    assert hasattr(config, 'DUPLICATE_THRESHOLD')
    assert hasattr(config, 'CLEANLINESS_MIN_CONFIDENCE')
    assert hasattr(config, 'TITLE_MIN_CONFIDENCE')

    # Ollama server pool
    assert hasattr(config, 'OLLAMA_SERVERS')
    assert hasattr(config, 'OLLAMA_LOCK_DIR')
    assert hasattr(config, 'OLLAMA_LOCK_RETRY_WAIT')
    assert hasattr(config, 'OLLAMA_LOCK_RETRY_MAX_ATTEMPTS')
    assert hasattr(config, 'OLLAMA_LOCK_RETRY_JITTER')

    # Ollama configs (new structure)
    assert hasattr(config, 'OLLAMA_CLEANLINESS_CHECK')
    assert hasattr(config, 'OLLAMA_FORMATTING')
    assert hasattr(config, 'OLLAMA_CATEGORIZATION')
    assert hasattr(config, 'OLLAMA_TITLE_GENERATION')
    assert isinstance(config.OLLAMA_CLEANLINESS_CHECK, dict)
    assert isinstance(config.OLLAMA_FORMATTING, dict)
    assert isinstance(config.OLLAMA_CATEGORIZATION, dict)
    assert isinstance(config.OLLAMA_TITLE_GENERATION, dict)
    
    # Categories (now in joke_categories module)
    assert hasattr(joke_categories, 'VALID_CATEGORIES')
    assert isinstance(joke_categories.VALID_CATEGORIES, list)
    assert len(joke_categories.VALID_CATEGORIES) > 0

    assert hasattr(joke_categories, 'MAX_CATEGORIES_PER_JOKE')
    
    # Logging
    assert hasattr(config, 'LOG_DIR')
    assert hasattr(config, 'LOG_LEVEL')
    
    # Error Handling
    assert hasattr(config, 'MAX_RETRIES')

def test_data_types():
    """Test that configuration values have correct data types."""
    # Timeouts should be integers
    assert isinstance(config.EXTERNAL_SCRIPT_TIMEOUT, int)
    assert isinstance(config.OLLAMA_TIMEOUT, int)

    # Thresholds should be integers
    assert isinstance(config.DUPLICATE_THRESHOLD, int)
    assert isinstance(config.CLEANLINESS_MIN_CONFIDENCE, int)
    assert isinstance(config.TITLE_MIN_CONFIDENCE, int)

    # MAX_RETRIES should be an integer
    assert isinstance(config.MAX_RETRIES, int)

    # MAX_CATEGORIES_PER_JOKE should be an integer
    assert isinstance(joke_categories.MAX_CATEGORIES_PER_JOKE, int)

    # LOG_LEVEL should be a string
    assert isinstance(config.LOG_LEVEL, str)

    # Ollama server pool config
    assert isinstance(config.OLLAMA_SERVERS, list)
    assert len(config.OLLAMA_SERVERS) > 0
    assert isinstance(config.OLLAMA_LOCK_RETRY_WAIT, (int, float))
    assert isinstance(config.OLLAMA_LOCK_RETRY_MAX_ATTEMPTS, int)
    assert isinstance(config.OLLAMA_LOCK_RETRY_JITTER, (int, float))

    # Ollama configs should be dictionaries with required keys
    for ollama_cfg in [config.OLLAMA_CLEANLINESS_CHECK, config.OLLAMA_FORMATTING,
                       config.OLLAMA_CATEGORIZATION, config.OLLAMA_TITLE_GENERATION]:
        assert 'OLLAMA_MODEL' in ollama_cfg
        assert 'OLLAMA_SYSTEM_PROMPT' in ollama_cfg
        assert 'OLLAMA_USER_PROMPT' in ollama_cfg
        assert 'OLLAMA_KEEP_ALIVE' in ollama_cfg
        assert 'OLLAMA_OPTIONS' in ollama_cfg
        assert isinstance(ollama_cfg['OLLAMA_OPTIONS'], dict)

def test_valid_categories():
    """Test that VALID_CATEGORIES is a non-empty list."""
    assert isinstance(joke_categories.VALID_CATEGORIES, list)
    assert len(joke_categories.VALID_CATEGORIES) > 0

def test_ollama_config_has_required_keys():
    """Test that ollama configs have all required keys."""
    required_keys = [
        'OLLAMA_MODEL',
        'OLLAMA_SYSTEM_PROMPT',
        'OLLAMA_USER_PROMPT',
        'OLLAMA_KEEP_ALIVE',
        'OLLAMA_OPTIONS'
    ]

    for ollama_cfg in [config.OLLAMA_CLEANLINESS_CHECK, config.OLLAMA_FORMATTING,
                       config.OLLAMA_CATEGORIZATION, config.OLLAMA_TITLE_GENERATION]:
        for key in required_keys:
            assert key in ollama_cfg, f"Missing key in ollama config: {key}"

        # Check options
        assert 'temperature' in ollama_cfg['OLLAMA_OPTIONS']
        assert 'num_ctx' in ollama_cfg['OLLAMA_OPTIONS']
        assert 'repeat_penalty' in ollama_cfg['OLLAMA_OPTIONS']
        assert 'top_k' in ollama_cfg['OLLAMA_OPTIONS']
        assert 'top_p' in ollama_cfg['OLLAMA_OPTIONS']
        assert 'min_p' in ollama_cfg['OLLAMA_OPTIONS']
        assert 'repeat_last_n' in ollama_cfg['OLLAMA_OPTIONS']

def test_pipeline_paths_exist():
    """Test that pipeline paths are properly set."""
    # Check that paths are strings
    assert isinstance(config.PIPELINE_MAIN, str)
    assert isinstance(config.PIPELINE_PRIORITY, str)
    assert len(config.PIPELINE_MAIN) > 0
    assert len(config.PIPELINE_PRIORITY) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])