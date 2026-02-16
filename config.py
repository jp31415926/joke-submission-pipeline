#!/usr/bin/env python3
"""
Configuration file for the joke submission pipeline.
"""

import os

# Directory paths
PIPELINE_MAIN = os.path.join(os.path.dirname(__file__), "pipeline-main")
PIPELINE_PRIORITY = os.path.join(os.path.dirname(__file__), "pipeline-priority")

STAGES = {
    "incoming": "01_incoming",
    "parsed": "02_parsed",
    "deduped": "03_deduped",
    "clean_checked": "04_clean_checked",
    "formatted": "05_formatted",
    "categorized": "06_categorized",
    "ready_for_review": "08_ready_for_review",
}

REJECTS = {
    "parse": "50_rejected_parse",
    "duplicate": "51_rejected_duplicate",
    "cleanliness": "52_rejected_cleanliness",
    "format": "53_rejected_format",
    "category": "54_rejected_category",
    "titled": "55_rejected_titled",
}

# Script paths
JOKE_EXTRACTOR = os.path.join(os.path.dirname(__file__), "joke-extractor", "joke-extract.py")
BUILD_TFIDF = os.path.join(os.path.dirname(__file__), "jokematch2", "build_tfidf.py")
SEARCH_TFIDF = os.path.join(os.path.dirname(__file__), "jokematch2", "search_tfidf.py")

# Thresholds
DUPLICATE_THRESHOLD = 70  # 0-100 score
CLEANLINESS_MIN_CONFIDENCE = 70  # 0-100
CATEGORIZATION_MIN_CONFIDENCE = 70  # 0-100

# Ollama LLM Configuration
ollama_config = {
    'ollama_api_url': 'http://localhost:11434/api/generate',
    'ollama_model': 'llama3',
    'ollama_prefix_prompt': 'You are a helpful assistant.',
    'ollama_think': False,
    'ollama_keep_alive': 0,
    'ollama_options': {
        'temperature': 0.7,
        'num_ctx': 65536,
        'repeat_penalty': 1.1,
        'top_k': 40,
        'top_p': 0.9,
        'min_p': 0.0,
        'repeat_last_n': 64,
    }
}

# Valid Categories
VALID_CATEGORIES = [
    # Humor Styles
    "Puns",
    "Wordplay", 
    "Dad Jokes",
    "Dark Humor",
    "Observational",
    "Knock-Knock",
    "One-Liners",
    "Anti-Jokes",
    
    # Topics
    "Animals",
    "Technology",
    "Food",
    "Sports",
    "Politics",
    "Relationships",
    "Work",
    "Kids",
    "School",
    "Science",
    "History",
    "Travel",
    
    # Occasions
    "Holiday",
    "Christmas",
    "Halloween", 
    "Thanksgiving",
    "Birthday",
    "Wedding",
    
    # Other
    "Clean",
    "Adult",
    "Topical"
]

MAX_CATEGORIES_PER_JOKE = 3

# Logging
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_LEVEL = "INFO"

# Error Handling
MAX_RETRIES = 2  # Retry twice (3 total attempts)