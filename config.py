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
JOKE_EXTRACTOR_DIR = os.path.join(os.path.dirname(__file__), "joke-extractor")
SEARCH_TFIDF_DIR = os.path.join(os.path.dirname(__file__), "jokematch2")
SEARCH_TFIDF_DATA_DIR = os.path.join(SEARCH_TFIDF_DIR, "data")
JOKE_EXTRACTOR = os.path.join(JOKE_EXTRACTOR_DIR, "joke-extract.py")
BUILD_TFIDF = os.path.join(SEARCH_TFIDF_DIR, "build_tfidf.py")
BUILD_TFIDF_OPTIONS = ['-a', SEARCH_TFIDF_DATA_DIR]
SEARCH_TFIDF = os.path.join(SEARCH_TFIDF_DIR, "search_tfidf.py")
SEARCH_TFIDF_OPTIONS = ['-1', '-a', SEARCH_TFIDF_DATA_DIR]

# Timeouts (in seconds)
EXTERNAL_SCRIPT_TIMEOUT = 60  # Timeout for external scripts (joke-extractor, TF-IDF)
OLLAMA_TIMEOUT = 300  # Timeout for Ollama LLM API calls

# Ollama Server Pool Configuration
# List of Ollama servers with their max concurrent requests
OLLAMA_SERVERS = [
  {"url": "http://localhost:11434", "max_concurrent": 1},
  # Add more servers as needed:
  {"url": "http://192.168.99.50:11434", "max_concurrent": 1},
]

# Ollama Server Locking Configuration
OLLAMA_LOCK_DIR = os.path.join(os.path.dirname(__file__), "locks", "ollama-servers")
#OLLAMA_LOCK_RETRY_WAIT = 5.0  # Base wait time between retries (seconds)
#OLLAMA_LOCK_RETRY_MAX_ATTEMPTS = 12  # Max retry attempts (5s * 12 = 60s total)
#OLLAMA_LOCK_RETRY_JITTER = 2.0  # Max random jitter to add to retry wait (seconds)
OLLAMA_LOCK_RETRY_WAIT = 10.0  # Base wait time between retries (seconds)
OLLAMA_LOCK_RETRY_MAX_ATTEMPTS = 720 # Max retry attempts (10s * 720 = 7200s = 2h total)
OLLAMA_LOCK_RETRY_JITTER = 5.0  # Max random jitter to add to retry wait (seconds)

# Thresholds
DUPLICATE_THRESHOLD = 60  # 0-100 score
CLEANLINESS_MIN_CONFIDENCE = 50  # 0-100
CATEGORIZATION_MIN_CONFIDENCE = 50  # 0-100
TITLE_MIN_CONFIDENCE = 50  # 0-100

# Ollama LLM Configuration - Cleanliness Check
# qwen3:8b https://huggingface.co/Qwen/Qwen3-8B
OLLAMA_CLEANLINESS_CHECK = {
  'OLLAMA_MODEL': 'qwen3:8b', # qwen3:8b, gemma3:4b gemma3:12b
  'OLLAMA_SYSTEM_PROMPT': 'You are a content moderator evaluating jokes. No markdown formatting',
  'OLLAMA_USER_PROMPT': '''Evaluate this joke for cleanliness and appropriateness:

{content}

Determine if this joke is:
- Clean (no profanity, sexual content, or offensive material)
- Appropriate for general audiences; no politics
- Give a confidence score of 0-100
- If status is FAIL, give a reason; otherwise leave "reason" blank

Respond ONLY with valid JSON in this exact format:
{{"status": "PASS or FAIL", "confidence": 0, "reason": "brief explanation"}}''',
  'OLLAMA_KEEP_ALIVE': '1m',
  'OLLAMA_OPTIONS': {
    'temperature': 0.7,
    'num_ctx': 65536,
    'repeat_penalty': 1.1,
    'top_k': 20,
    'top_p': 0.8,
    'min_p': 0.0,
    'repeat_last_n': 64,
  }
}

# Ollama LLM Configuration - Formatting
OLLAMA_FORMATTING = {
  'OLLAMA_MODEL': 'gemma3:12b', # qwen3:8b, gemma3:4b
  'OLLAMA_SYSTEM_PROMPT': 'You are an editor improving joke formatting and grammar. Always start with double quotes for quoted parts. No markdown formatting',
  'OLLAMA_USER_PROMPT': '''Improve the grammar, punctuation, and formatting of this joke while preserving its meaning and humor:

{content}

- Give a confidence score of 0-100
Respond ONLY with valid JSON in this exact format:
{{"formatted_joke": "the improved joke text here", "confidence": 0, "changes": "brief description of changes"}}''',
  'OLLAMA_KEEP_ALIVE': '1m',
  'OLLAMA_OPTIONS': {
    'temperature': 0.7,
    'num_ctx': 65536,
    'repeat_penalty': 1.1,
    'top_k': 20,
    'top_p': 0.8,
    'min_p': 0.0,
    'repeat_last_n': 64,
  }
}

# Ollama LLM Configuration - Categorization
OLLAMA_CATEGORIZATION = {
  'OLLAMA_MODEL': 'gemma3:12b', # qwen3:8b, gemma3:4b
  'OLLAMA_SYSTEM_PROMPT': 'You are a joke categorization expert. No markdown formatting',
  'OLLAMA_USER_PROMPT': '''Categorize this joke into 1-3 categories from this list:
{categories_list}

Joke:
{content}

- Give a confidence score of 0-100
- If status is FAIL, give a reason; otherwise leave reason blank
Respond ONLY with valid JSON in this exact format:
{{"categories": ["Category1", "Category2"], "confidence": 0, "reason": "brief explanation"}}''',
  'OLLAMA_KEEP_ALIVE': '1m',
  'OLLAMA_OPTIONS': {
    'temperature': 0.7,
    'num_ctx': 65536,
    'repeat_penalty': 1.1,
    'top_k': 20,
    'top_p': 0.8,
    'min_p': 0.0,
    'repeat_last_n': 64,
  }
}

# Ollama LLM Configuration - Title Generation
OLLAMA_TITLE_GENERATION = {
  'OLLAMA_MODEL': 'gemma3:12b', # qwen3:8b, gemma3:4b
  'OLLAMA_SYSTEM_PROMPT': 'You are a creative title writer for jokes. No markdown formatting',
  'OLLAMA_USER_PROMPT': '''Create a short, catchy title for this joke:

{content}

Categories: {categories}

- Give a confidence score of 0-100
Respond ONLY with valid JSON in this exact format:
{{"title": "A Short Catchy Title", "confidence": 0}}''',
  'OLLAMA_KEEP_ALIVE': '1m',
  'OLLAMA_OPTIONS': {
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
    "Family",
    "Food",
    "History",
    "Kids",
    "Politics",
    "Relationships",
    "School",
    "Science",
    "Sports",
    "Technology",
    "Travel",
    "Work",
    
    # Occasions
    "Holiday",
    "Christmas",
    "Halloween", 
    "Thanksgiving",
    "Birthday",
    "Wedding",
    "New Year's Day",
    "Independence Day",
    "Veteran's Day",
    
    # Other
    "Topical"
]

MAX_CATEGORIES_PER_JOKE = 3

# Logging
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_LEVEL = "INFO"

# Error Handling
MAX_RETRIES = 0  # Retry twice (3 total attempts)