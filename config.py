#!/usr/bin/env python3
"""
Configuration file for the joke submission pipeline.
"""

import os

# Directory paths
PIPELINE_MAIN = os.path.join(os.path.dirname(__file__), "pipeline-main")
PIPELINE_PRIORITY = os.path.join(os.path.dirname(__file__), "pipeline-priority")

STAGES = {
    "parse": "01_parse",
    "dedup": "02_dedup",
    "clean_check": "03_clean_check",
    "format": "04_format",
    "categorize": "05_categorize",
    "title": "06_title",
    "ready_for_review": "08_ready_for_review",
}

REJECTS = {
    "parse": "50_rejected_parse",
    "dedup": "51_rejected_dedup",
    "clean_check": "52_rejected_clean_check",
    "format": "53_rejected_format",
    "categorize": "54_rejected_categorize",
    "title": "55_rejected_title",
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
  #{"url": "http://192.168.99.50:11434", "max_concurrent": 1},
  #{"url": "http://192.168.99.69:11434", "max_concurrent": 1},
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
TITLE_MIN_CONFIDENCE = 50  # 0-100

# Ollama LLM Configuration - Cleanliness Check
# qwen3:8b https://huggingface.co/Qwen/Qwen3-8B
OLLAMA_CLEANLINESS_CHECK = {
  'OLLAMA_MODEL': 'mistral-nemo:12b', # qwen3:8b, gemma3:4b gemma3:12b
  'OLLAMA_SYSTEM_PROMPT': 'You are an English-speaking strict content safety reviewer.',
  'OLLAMA_USER_PROMPT': '''Your task is to evaluate the following joke for cleanliness and appropriateness.

Assess the joke for:
- profanity or crude language
- sexual content or innuendo
- hate, harassment, or slurs
- violence or threats
- adult or explicit themes
- discriminatory or demeaning language

DEFINITIONS:
- "PASS" means the joke is clean and appropriate for a general audience.
- "FAIL" means the joke contains any content that may be inappropriate, offensive, or unsafe.

SCORING:
- Give a confidence score from 0 to 100 indicating how certain you are in your PASS/FAIL decision.

OUTPUT RULES:
- Return ONLY a single JSON object.
- Use this exact structure and field names:
{{"status": "PASS" or "FAIL", "confidence": <integer 0-100>, "reason": "<brief explanation>"}}

Do NOT include any text outside the JSON.

Joke:
{content}
''',
  'OLLAMA_KEEP_ALIVE': 0,#1m
  'OLLAMA_OPTIONS': {
    'temperature': 0.2,
    'num_ctx': 65536,
    'repeat_penalty': 1.05,
    'top_k': 20,
    'top_p': 0.9,
    'min_p': 0.05,
    'repeat_last_n': 32,
  }
}

# Ollama LLM Configuration - Formatting
OLLAMA_FORMATTING = {
  'OLLAMA_MODEL': 'qwen2.5:7b', # qwen3:8b, gemma3:4b, gemma3:12b, llama3.2:3b
  'OLLAMA_SYSTEM_PROMPT': 'You are an English-speaking literal text correction engine.',
  'OLLAMA_USER_PROMPT': '''Your only task is to fix:

* Spelling
* Grammar
* Punctuation
* Minor clarity issues caused strictly by grammar errors

Rules:

1. Keep the exact meaning.
2. Do NOT change tone.
3. Do NOT rewrite for style.
4. Do NOT rephrase sentences unless required to fix grammar.
5. Do NOT add ideas.
6. Do NOT remove ideas.
7. Do NOT make the text more formal or more casual.
8. Preserve all paragraph breaks and line breaks exactly.
9. Do NOT use markdown.
10. Do NOT use em dashes.
11. If a sentence is grammatically correct, leave it unchanged.

Important:

* Make the minimum number of edits required.
* If no corrections are needed, return the text exactly as provided.

Output format (must match exactly):

Confidence: <0-100>
Changes: <brief description of what changed, or None>

<corrected text here, preserving original structure exactly>

Text to correct:
{content}
''',
  'OLLAMA_KEEP_ALIVE': 0,#1m
  'OLLAMA_OPTIONS': {
    'temperature': 0.0,
    'num_ctx': 65536,
    'repeat_penalty': 1.0,
    'top_k': 1,
    'top_p': 1.0,
    'min_p': 0.0,
    'repeat_last_n': 0,
  }
}


# Ollama LLM Configuration - Categorization
OLLAMA_CATEGORIZATION = {
  'OLLAMA_MODEL': 'mistral-nemo:12b', # qwen3:8b, gemma3:4b
  'OLLAMA_SYSTEM_PROMPT': 'You are an English-speaking strict multi-label classifier.',
  'OLLAMA_USER_PROMPT': '''TASK:
Select one or more categories from the <categories> list that best match the joke.

RULES:
- You MUST select at least one category.
- You MUST use ONLY exact category names from the list.
- Do NOT create, modify, or infer new category names.
- If no perfect match exists, choose the closest reasonable match.
- Sort selected categories from best match to weakest match.
- Returning zero categories is an automatic FAIL.

FAIL CONDITIONS:
- Zero categories selected
- Any category not in the provided list
- Any deviation from the required JSON format

OUTPUT:
Return ONLY a single valid JSON object in this exact structure:

{{"categories": ["Category1", "Category2"], "reason": "brief explanation" }}

If you fail any rule, return:

{{"categories": [], "reason": "FAIL"}}

<categories>
{categories_list}
</categories>

Joke:
{content}
''',
  'OLLAMA_KEEP_ALIVE': 0,#1m
  'OLLAMA_OPTIONS': {
    'temperature': 0.1,
    'num_ctx': 65536,
    'repeat_penalty': 1.1,
    'top_k': 20,
    'top_p': 0.9,
    'min_p': 0.05,
    'repeat_last_n': 64,
  }
}


# Ollama LLM Configuration - Title Generation
OLLAMA_TITLE_GENERATION = {
  'OLLAMA_MODEL': 'qwen2.5:14b', # qwen3:8b, gemma3:4b
  'OLLAMA_SYSTEM_PROMPT': 'You are an English-speaking expert comedy headline writer specializing in dry, clever, and pun-based humor',
  'OLLAMA_USER_PROMPT': '''Task: Create a punchy, thematic, fun title for the provided joke.

Constraints:
- Length: 2-8 words
- Format: Title Case
- Style: Relate specifically to the theme, irony or punchline
- Negative Constraints: No quotation marks, no terminal punctuation, no generic fillers.

Return ONLY valid JSON in this format:
{{"title": "string", "reasoning": "string", "confidence": int (0-100)}}

Joke:
{content}
''',
  'OLLAMA_KEEP_ALIVE': 0,#1m
  'OLLAMA_OPTIONS': {
    'temperature': 0.7,
    'num_ctx': 65536,
    'repeat_penalty': 1.05,
    'top_k': 50,
    'top_p': 0.9,
    'min_p': 0.05,
    'repeat_last_n': 64,
  }
}

# Logging
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_LEVEL = "WARNING"

# Error Handling
MAX_RETRIES = 1  # Retry twice (3 total attempts)

# Emergency Stop
# Create this file to gracefully stop all stage processing
ALL_STOP = os.path.join(os.path.dirname(__file__), "ALL_STOP")