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
EXTERNAL_SCRIPT_TIMEOUT = 120  # Timeout for external scripts (joke-extractor, TF-IDF)
OLLAMA_TIMEOUT = 3600  # Timeout for Ollama LLM API calls

# Ollama Server Pool Configuration
# List of Ollama servers with their max concurrent requests
OLLAMA_SERVERS = [
  {"url": "http://localhost:11434", "max_concurrent": 1},
  # Add more servers as needed:
  {"url": "http://192.168.99.50:11434", "max_concurrent": 1},
  {"url": "http://192.168.99.69:11434", "max_concurrent": 1},
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
  'OLLAMA_MODEL': 'llama3.1:8b', # qwen3:8b, gemma3:4b gemma3:12b
  'OLLAMA_SYSTEM_PROMPT': 'You are a content moderator evaluating jokes. No markdown formatting',
  'OLLAMA_USER_PROMPT': '''Evaluate this joke for cleanliness and appropriateness:
Determine if this joke is:
- Clean (no profanity, sexual content, or offensive material)
- Appropriate for general audiences; no politics
- Give a confidence score of 0-100
- If status is FAIL, give a reason; otherwise leave "reason" blank
Respond ONLY with valid JSON in this exact format:
{{"status": "PASS or FAIL", "confidence": 0, "reason": "brief explanation"}}

<joke>
{content}
</joke>''',
  'OLLAMA_KEEP_ALIVE': '1m',
  'OLLAMA_OPTIONS': {
    'temperature': 0.4,
    'num_ctx': 65536,
    'repeat_penalty': 1.1,
    'top_k': 15,
    'top_p': 0.7,
    'min_p': 0.0,
    'repeat_last_n': 64,
  }
}

# Ollama LLM Configuration - Formatting
OLLAMA_FORMATTING = {
  'OLLAMA_MODEL': 'llama3.1:8b', # qwen3:8b, gemma3:4b, gemma3:12b, llama3.2:3b
  'OLLAMA_SYSTEM_PROMPT': 'You are an editor improving joke formatting and grammar',
  'OLLAMA_USER_PROMPT': '''Correct the grammar, spelling, and punctuation of the following text.
- Do not change the wording or tone unless it is necessary for clarity.
- Keep the joke's punchline intact.
- No markdown formatting. Do not use em dashes
- Give a confidence score of 0-100
- Respond ONLY with valid JSON in this exact format:
{{"formatted_joke": "the improved joke text here", "confidence": 0, "changes": "brief description of changes, or None"}}

<joke>
{content}
</joke>''',
  'OLLAMA_KEEP_ALIVE': '1m',
  'OLLAMA_OPTIONS': {
    'temperature': 0.4,
    'num_ctx': 65536,
    'repeat_penalty': 1.1,
    'top_k': 15,
    'top_p': 0.7,
    'min_p': 0.0,
    'repeat_last_n': 64,
  }
}

# Ollama LLM Configuration - Categorization
OLLAMA_CATEGORIZATION = {
  'OLLAMA_MODEL': 'llama3.1:8b', # qwen3:8b, gemma3:4b
  'OLLAMA_SYSTEM_PROMPT': 'You are a joke categorization expert. No markdown formatting',
  'OLLAMA_USER_PROMPT': '''Categorize this joke into as many categories you can come up with, sorted with the best ones first
- Give a confidence score of 0-100
- If status is FAIL, give a reason; otherwise leave reason blank
- Respond ONLY with valid JSON in this exact format:
{{"categories": ["Category1", "Category2"], "confidence": 0, "reason": "brief explanation"}}

<joke>
{content}
</joke>''',
  'OLLAMA_KEEP_ALIVE': '1m',
  'OLLAMA_OPTIONS': {
    'temperature': 0.8,
    'num_ctx': 65536,
    'repeat_penalty': 1.1,
    'top_k': 40,
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
- Give a confidence score of 0-100
- Respond ONLY with valid JSON in this exact format:
{{"title": "A Short Catchy Title", "confidence": 0}}

<categories>
{categories}
</categories>

<joke>
{content}
</joke>''',
  'OLLAMA_KEEP_ALIVE': '1m',
  'OLLAMA_OPTIONS': {
    'temperature': 0.8,
    'num_ctx': 65536,
    'repeat_penalty': 1.1,
    'top_k': 60,
    'top_p': 0.9,
    'min_p': 0.0,
    'repeat_last_n': 64,
  }
}

# Logging
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_LEVEL = "INFO"

# Error Handling
MAX_RETRIES = 1  # Retry twice (3 total attempts)

# Emergency Stop
# Create this file to gracefully stop all stage processing
ALL_STOP = os.path.join(os.path.dirname(__file__), "ALL_STOP")