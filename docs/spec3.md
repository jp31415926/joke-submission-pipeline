# Joke Submission Pipeline — Developer Specification v1.1

## 1. Overview

This pipeline processes joke submissions from emails into a ready-for-review state. It is **batch-oriented, file-based**, and uses independent stages to transform submissions. Final database insertion is handled by a separate project (out of scope).

---

## 2. Environment

* Single Linux machine
* Python 3.x
* Local LLM (Ollama with llama3 model) for cleanliness, formatting, categorization, title generation
* Cron used for batch orchestration
* Expected volume: 1-10 jokes per day (low volume)
* Batch size: 1 file per stage execution

---

## 3. File-Based State Machine

### 3.1 Directory Structure

Directory names are specified in the `config.py` file. Scripts should not hard code directory names, but instead use config.py variables.
Example: main incoming stage directory would be `os.path.join(config.PIPELINE_MAIN, config.STAGES["incoming"])`

**Each stage directory contains a `tmp/` subdirectory for atomic file operations.**

```
project-root/
├── joke-pipeline.py             # Primary script
├── joke-extractor/               
│   └── joke-extract.py          # joke extract script
├── jokematch2/                  
│   ├── build_tfidf.py           # joke dedup TF-IDF vector builder script
│   └── search_tfidf.py          # joke dedup search script
├── pipeline-main/               # MAIN pipeline top level directory
│   ├── 01_incoming/             # Newly arrived jokes from Maildir
│   │   └── tmp/                 # Temp directory for atomic operations
│   ├── 02_parsed/               # Post email parsing
│   │   └── tmp/
│   ├── 03_deduped/              # After duplicate check
│   │   └── tmp/
│   ├── 04_clean_checked/        # After cleanliness check
│   │   └── tmp/
│   ├── 05_formatted/            # After grammar/punctuation formatting
│   │   └── tmp/
│   ├── 06_categorized/          # After category assignment
│   │   └── tmp/
│   ├── 07_titled/               # After title assignment
│   │   └── tmp/
│   ├── 08_ready_for_review/     # Completed jokes ready for human review
│   │   └── tmp/
│   ├── 50_rejected_parse/       # Failed parsing
│   ├── 51_rejected_duplicate/   # Failed duplicate check
│   ├── 52_rejected_cleanliness/ # Failed cleanliness check
│   ├── 53_rejected_format/      # Failed formatting
│   ├── 54_rejected_category/    # Failed category assignment
│   └── 55_rejected_titled/      # Failed title assignment
├── pipeline-priority/           # PRIORITY pipeline top level directory
│   ├── 01_incoming/             # Newly arrived jokes from Maildir
│   │   └── tmp/
│   ├── 02_parsed/               # Post email parsing
│   │   └── tmp/
│   ├── 03_deduped/              # After duplicate check
│   │   └── tmp/
│   ├── 04_clean_checked/        # After cleanliness check
│   │   └── tmp/
│   ├── 05_formatted/            # After grammar/punctuation formatting
│   │   └── tmp/
│   ├── 06_categorized/          # After category assignment
│   │   └── tmp/
│   ├── 07_titled/               # After title assignment
│   │   └── tmp/
│   ├── 08_ready_for_review/     # Completed jokes ready for human review
│   │   └── tmp/
│   ├── 50_rejected_parse/       # Failed parsing
│   ├── 51_rejected_duplicate/   # Failed duplicate check
│   ├── 52_rejected_cleanliness/ # Failed cleanliness check
│   ├── 53_rejected_format/      # Failed formatting
│   ├── 54_rejected_category/    # Failed category assignment
│   └── 55_rejected_titled/      # Failed title assignment
└── tests/
    ├── test_abc.py
    └── ...
```

**Pipeline-Priority:**

* Mirrors the `pipeline-main/` structure
* Scripts check `pipeline-priority/` first for files
* Files in `pipeline-priority/` remain independent of `pipeline-main/`
* Priority routing is out of scope; when files appear in priority pipeline, they are processed

---

### 3.2 File Format (Plain Text + Header)

Each joke candidate is a **single text file**, named by UUID:

```
<Joke-ID>.txt
```

#### Initial File Format (from joke-extract.py)

Example joke output from joke-extract.py:

```
Title: Colorful Meal
Submitter: "'Thomas S. Ellsworth' tellswor@kcbx.net [good-clean-fun]" <good-clean-fun-noreply@yahoogroups.com>

Over dinner, I explained the health benefits of a colorful meal to my family. "The more colors, the more variety of nutrients," I told them. Pointing to our food, I asked, "How many different colors do you see?"

"Six," volunteered my daughter. "Seven if you count the burned parts."
```

**Initial Fields** (from joke-extract.py):
* **Title**: May be blank if not found in email
* **Submitter**: Copy of original From: header 

**Note**: The pipeline wrapper adds the Joke-ID UUID as the filename and must populate additional metadata fields as files progress through stages.

#### Complete Header Structure (as files progress)

Header structure (key: value), followed by blank line separator:

```
Joke-ID: 550e8400-e29b-41d4-a716-446655440000
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
```

### 3.3 Metadata Field Progression by Stage

| Field                    | Populated By Stage | Notes                                    |
| ------------------------ | ------------------ | ---------------------------------------- |
| Title                    | joke-extract.py    | May be blank; filled by titled stage     |
| Submitter                | joke-extract.py    | Raw From: header                         |
| Joke-ID                  | 01_incoming        | UUID generated by pipeline wrapper       |
| Source-Email-File        | 01_incoming        | Original Maildir filename                |
| Pipeline-Stage           | All stages         | Updated as file progresses               |
| Duplicate-Score          | 02_parsed          | 0-100 integer from search_tfidf.py       |
| Duplicate-Threshold      | 02_parsed          | Threshold from config (default 70)       |
| Cleanliness-Status       | 03_deduped         | PASS or FAIL                             |
| Cleanliness-Confidence   | 03_deduped         | 0-100 integer                            |
| Format-Status            | 04_clean_checked   | PASS or FAIL                             |
| Format-Confidence        | 04_clean_checked   | 0-100 integer                            |
| Categories               | 05_formatted       | Comma-separated list                     |
| Category-Confidence      | 05_formatted       | 0-100 integer                            |
| Rejection-Reason         | Any reject stage   | Description of why rejected              |

**Notes:**
* **Title field MAY be blank** until `titled/` stage
* **Confidence scores** are integers 0-100 (not floats)
* All metadata stored inline in file header
* Files are named with **UUID** for uniqueness

---

## 4. Pipeline Stages & Integration

### 4.1 Stage Summary

| Stage                    | Input                | Processing                                      | Output               | Rejection                | Integration Notes                                                  |
| ------------------------ | -------------------- | ----------------------------------------------- | -------------------- | ------------------------ | ------------------------------------------------------------------ |
| **01_incoming/**         | Maildir email        | Call `joke-extract.py`, generate UUID, add meta | 02_parsed/           | 50_rejected_parse/       | Wrapper generates Joke-ID UUID, adds Source-Email-File             |
| **02_parsed/**           | 01_incoming/         | Duplicate check using `search_tfidf.py`         | 03_deduped/          | 51_rejected_duplicate/   | Output parsed; score > threshold = reject                          |
| **03_deduped/**          | 02_parsed/           | Cleanliness LLM check                           | 04_clean_checked/    | 52_rejected_cleanliness/ | Confidence must be >= 70 (configurable)                            |
| **04_clean_checked/**    | 03_deduped/          | Formatting LLM                                  | 05_formatted/        | 53_rejected_format/      | Updates joke content with formatted version                        |
| **05_formatted/**        | 04_clean_checked/    | Categorization LLM                              | 06_categorized/      | 54_rejected_category/    | Confidence must be >= 70 (configurable); assigns 1-10 categories   |
| **06_categorized/**      | 05_formatted/        | Title generation LLM (only if blank)            | 07_titled/           | 55_rejected_titled/      | Skips jokes with existing title                                    |
| **07_titled/**           | 06_categorized/      | Final validation                                | 08_ready_for_review/ | 55_rejected_titled/      | Validates all required fields present                              |
| **08_ready_for_review/** | 07_titled/           | Manual review (out of scope)                    | N/A                  | N/A                      | Holding area; reviewers manually move files (outside this project) |

---

### 4.2 Existing Script Execution

#### joke-extract.py

* **Location**: Path specified in `config.py` (config.JOKE_EXTRACTOR)
* **Invocation**: `joke-extract.py <email_file> <success_dir> <fail_dir>`
* **Input**: Single Maildir email file
* **Output**: 
  - Zero or more joke files in `<success_dir>`
  - Each file contains only: `Title:` header (may be blank), `Submitter:` header, blank line, joke body
  - Filenames are arbitrary (pipeline will rename to UUID)
* **Exit Code**: 
  - 0 = success
  - Non-zero = failure
* **Email Format**: Standard Maildir format
* **Multi-joke Emails**: Script determines how to split; may create multiple files from one email

**Pipeline Wrapper Responsibilities**:
1. Call joke-extract.py with appropriate directories
2. For each output file created:
   - Generate UUID for Joke-ID
   - Rename file to `<UUID>.txt`
   - Add Joke-ID header field
   - Add Source-Email-File header field (original email filename)
   - Add Pipeline-Stage field
   - Move to 02_parsed directory

#### search_tfidf.py

* **Location**: Path specified in `config.py` (config.SEARCH_TFIDF)
* **Invocation**: `search_tfidf.py -1 -a <SEARCH_TFIDF_DATA_DIR> <joke_file>`
  - `SEARCH_TFIDF_DATA_DIR` is the `data` directory inside the `jokematch2` directory
  - `SEARCH_TFIDF_DATA_DIR` should be defined in `config.py`
* **Input**: Single joke file path
  - Joke file must contain the joke text, no headers
* **Output**: Single line to stdout like: `91 9278 A Meaningful New Year's Gesture`
  - First integer (0-100) is match score
  - Remaining text is details about matched joke (ignore)
* **Exit Code**: 
  - 0 = success
  - Non-zero = failure
* **Functionality**: Searches archive using pre-built TF-IDF vectors; internal details not relevant

**Pipeline Wrapper Responsibilities**:
1. Call search_tfidf.py with joke file path
2. Parse first integer from output (match score)
3. Compare score against config.DUPLICATE_THRESHOLD (default 70)
4. If score >= threshold: reject as duplicate
5. If score < threshold: pass as unique
6. Update header with Duplicate-Score and Duplicate-Threshold
7. If rejected, add Rejection-Reason

#### build_tfidf.py

* **Location**: Path specified in `config.py` (config.BUILD_TFIDF)
* **Invocation**: `build_tfidf.py -a <SEARCH_TFIDF_DATA_DIR>`
  - `SEARCH_TFIDF_DATA_DIR` is the `data` directory inside the `jokematch2` directory
* **Scheduled**: 3am weekdays via cron
* **Functionality**: Builds TF-IDF vector files for search_tfidf.py to use
* **Output**: None (stores vectors in appropriate location internally)
* **Exit Code**: 
  - 0 = success
  - Non-zero = failure

---

### 4.3 Multi-Joke Emails

* joke-extract.py handles splitting emails with multiple jokes
* Each joke extracted becomes a **separate file**
* Pipeline wrapper processes each output file independently
* Each joke is processed independently through all stages

---

### 4.4 Error Handling & Retry Logic

* **Retry Policy**: Each stage attempts processing up to 2 times (3 total attempts including initial)
* **After Retries Exhausted**: Move file to appropriate reject directory with Rejection-Reason
* **Failures Logged**: All errors logged with Joke-ID prefix when available
* **Files on Failure**: Remain in reject directory for manual inspection
* **Manual Reinjection**: Out of scope for this project

---

### 4.5 Logging

* Logs include: start/stop timestamps, files processed, errors, skips
* All log messages should prefix with Joke-ID when available
* Success processing logged at DEBUG level
* Logging paths configurable in `config.py`
* Log verbosity set in `config.py`, default to INFO
* **Log Rotation**: Out of scope for this version

---

### 4.6 Cron Orchestration

* Separate cron job per stage
* LLM stages may run slower; independent stages prevent blocking
* Pipeline-priority checked first for files, then pipeline-main
* Build TF-IDF scheduled 3am weekdays
* Each stage moves files as it operates on them
* No return codes examined by orchestration (stages do all work)

---

### 4.7 Atomic File Operations

* All file moves must be atomic:
  1. Write to `tmp/` subdirectory within destination stage directory
  2. Once complete, move (rename) from tmp/ to parent directory
* This prevents partial files from being processed
* Each stage directory contains a `tmp/` subdirectory for this purpose
* Only one cron job reads from and one writes to any queue directory

---

## 5. LLM Integration (Ollama)

### 5.1 Configuration

LLM configuration in `config.py`:

```python
ollama_config = {
    'ollama_api_url': 'http://localhost:11434/api/generate',
    'ollama_model': 'llama3',
    'ollama_prefix_prompt': 'You are a helpful assistant.',
    'ollama_think': False,
    'ollama_keep_alive': 0,
    'ollama_options': {
        'temperature': 0.7,  # Configurable
        'num_ctx': 65536,
        'repeat_penalty': 1.1,
        'top_k': 40,
        'top_p': 0.9,
        'min_p': 0.0,
        'repeat_last_n': 64,
    }
}
```

### 5.2 API Usage

* **Endpoint**: POST to `/api/generate`
* **Method**: Ollama generate API
* **Streaming**: Disabled (`stream: False`)
* **Response Format**: JSON with `response` field containing generated text

### 5.3 LLM Stages

* **Cleanliness Check** (03_deduped → 04_clean_checked)
  - Status: PASS or FAIL
  - Confidence: 0-100 integer
  - Minimum confidence threshold: 70 (configurable in config.py)
  
* **Formatting** (04_clean_checked → 05_formatted)
  - Returns formatted joke text
  - Confidence: 0-100 integer
  - Updates joke content
  
* **Categorization** (05_formatted → 06_categorized)
  - Returns 1-10 categories from valid list
  - Confidence: 0-100 integer
  - Minimum confidence threshold: 70 (configurable in config.py)
  
* **Title Generation** (06_categorized → 07_titled)
  - Only if Title field is blank
  - Returns suggested title
  - Confidence: 0-100 integer

**Confidence Thresholds**:
* Default minimum confidence: 70 (configurable per stage in config.py)
* LLM prompts should request confidence as integer 0-100
* If confidence < threshold: reject to appropriate reject directory

---

## 6. Valid Categories

Categories are configurable in `config.py`. Default categories:

```python
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

MAX_CATEGORIES_PER_JOKE = 10
```

**Categorization Rules**:
* Assign 1-10 most relevant categories
* All categories must be from VALID_CATEGORIES list
* Invalid categories are filtered out
* If no valid categories after filtering: reject to 54_rejected_category

---

## 7. Manual Review Process

* **08_ready_for_review/** is a holding area for manual review
* Reviewers manually inspect jokes and decide to:
  - Approve: move to another location (outside this project's scope)
  - Reject: move to a reject directory (outside this project's scope)
* **This project's responsibility**: Get jokes to ready_for_review with all required fields populated
* **Out of Scope**: What happens after manual review, database insertion, approval workflow

---

## 8. Ready for Review Validation

Before moving to `08_ready_for_review/`, validate:

**Required Fields** (must not be blank):
* Joke-ID (valid UUID)
* Title
* Submitter
* Source-Email-File
* Pipeline-Stage
* Categories (comma-separated list)
* Cleanliness-Status (must be PASS)
* Format-Status (must be PASS)

**Required Content**:
* Joke content must exist (non-empty)
* Joke content must be reasonable length (> 10 characters)

**If Validation Fails**:
* Move to 55_rejected_titled (or appropriate reject directory)
* Add Rejection-Reason with specific validation failures

---

## 9. Config File (`config.py`)

Example structure:

```python
# Directory paths
PIPELINE_MAIN = "/path/to/pipeline-main"
PIPELINE_PRIORITY = "/path/to/pipeline-priority"

STAGES = {
    "incoming": "01_incoming",
    "parsed": "02_parsed",
    "deduped": "03_deduped",
    "clean_checked": "04_clean_checked",
    "formatted": "05_formatted",
    "categorized": "06_categorized",
    "titled": "07_titled",
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
JOKE_EXTRACTOR_DIR = "/path/to/joke-extractor"
SEARCH_TFIDF_DIR = "/path/to/jokematch2"
SEARCH_TFIDF_DATA_DIR = SEARCH_TFIDF_DIR + "/data"
JOKE_EXTRACTOR = JOKE_EXTRACTOR_DIR + "/joke-extract.py"
BUILD_TFIDF = SEARCH_TFIDF_DIR + "/build_tfidf.py"
BUILD_TFIDF_OPTIONS = ['-a', SEARCH_TFIDF_DATA_DIR]
SEARCH_TFIDF = SEARCH_TFIDF_DIR + "/search_tfidf.py"
SEARCH_TFIDF_OPTIONS = ['-1','-a', SEARCH_TFIDF_DATA_DIR]

# Timeouts (in seconds)
EXTERNAL_SCRIPT_TIMEOUT = 60  # For joke-extractor, TF-IDF scripts
OLLAMA_TIMEOUT = 300  # For LLM API calls

# Thresholds
DUPLICATE_THRESHOLD = 70  # 0-100 score
CLEANLINESS_MIN_CONFIDENCE = 70  # 0-100
CATEGORIZATION_MIN_CONFIDENCE = 70  # 0-100
TITLE_MIN_CONFIDENCE = 70  # 0-100

# Ollama LLM Configuration - Cleanliness Check
OLLAMA_CLEANLINESS_CHECK = {
  'OLLAMA_API_URL': 'http://localhost:11434/api/generate',
  'OLLAMA_MODEL': 'qwen3:8b',
  'OLLAMA_SYSTEM_PROMPT': 'You are a content moderator evaluating jokes for appropriateness',
  'OLLAMA_USER_PROMPT': '''Evaluate this joke for cleanliness:
{content}

Respond ONLY with valid JSON:
{{"status": "PASS or FAIL", "confidence": 85, "reason": "brief explanation"}}''',
  'OLLAMA_KEEP_ALIVE': 0,
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

# Ollama LLM Configuration - Formatting
OLLAMA_FORMATTING = {
  'OLLAMA_API_URL': 'http://localhost:11434/api/generate',
  'OLLAMA_MODEL': 'qwen3:8b',
  'OLLAMA_SYSTEM_PROMPT': 'You are an editor improving joke formatting and grammar. Always start with double quotes for quoted parts',
  'OLLAMA_USER_PROMPT': '''Improve grammar of this joke:
{content}

Respond ONLY with valid JSON:
{{"formatted_joke": "improved text", "confidence": 85, "changes": "description"}}''',
  'OLLAMA_KEEP_ALIVE': 0,
  'OLLAMA_OPTIONS': {...}
}

# Ollama LLM Configuration - Categorization
OLLAMA_CATEGORIZATION = {
  'OLLAMA_API_URL': 'http://localhost:11434/api/generate',
  'OLLAMA_MODEL': 'qwen3:8b',
  'OLLAMA_SYSTEM_PROMPT': 'You are a joke categorizer. Keep responses short.',
  'OLLAMA_USER_PROMPT': '''Categorize this joke (1-10 categories):
{categories_list}

Joke: {content}

Respond ONLY with valid JSON:
{{"categories": ["Cat1", "Cat2"], "confidence": 85, "reason": "explanation"}}''',
  'OLLAMA_KEEP_ALIVE': 0,
  'OLLAMA_OPTIONS': {...}
}

# Ollama LLM Configuration - Title Generation
OLLAMA_TITLE_GENERATION = {
  'OLLAMA_API_URL': 'http://localhost:11434/api/generate',
  'OLLAMA_MODEL': 'qwen3:8b',
  'OLLAMA_SYSTEM_PROMPT': 'You are a title writer. Keep responses short.',
  'OLLAMA_USER_PROMPT': '''Create a title for this joke:
{content}

Categories: {categories}

Respond ONLY with valid JSON:
{{"title": "Short Title", "confidence": 85}}''',
  'OLLAMA_KEEP_ALIVE': 0,
  'OLLAMA_OPTIONS': {...}
}

# Valid Categories (Adult removed - not appropriate, flagged in cleanliness check)
VALID_CATEGORIES = [
    "Puns", "Wordplay", "Dad Jokes", "Dark Humor", "Observational",
    "Knock-Knock", "One-Liners", "Anti-Jokes",
    "Animals", "Technology", "Food", "Sports", "Politics",
    "Relationships", "Work", "Kids", "School", "Science",
    "History", "Travel",
    "Holiday", "Christmas", "Halloween", "Thanksgiving",
    "Birthday", "Wedding",
    "Clean", "Topical"
]
MAX_CATEGORIES_PER_JOKE = 10

# Logging
LOG_DIR = "/path/to/logs"
LOG_LEVEL = "INFO"

# Error Handling
MAX_RETRIES = 2  # Retry twice (3 total attempts)
```

* All scripts read paths and parameters from `config.py`
* Easy to change directories, thresholds, or script paths without modifying pipeline scripts
* All thresholds, categories, and LLM settings are configurable

---

## 10. Testing Plan

* Test with small batch of emails in `pipeline-main/` and `pipeline-priority/`
* Verify stage transitions, metadata, duplicate scoring, title generation
* Confirm atomic moves, logging, and LLM confidence updates
* Inspect reject directories
* Test retry logic (2 retries then reject)
* Test confidence threshold enforcement
* Sample emails will be provided for testing
* All other test decisions are developer choices

---

## 11. Stage Responsibilities Summary

Each stage is responsible for:

1. **Reading** files from its input directory
2. **Processing** files according to stage logic
3. **Moving** files to:
   - Output directory (on success) using atomic moves via tmp/ subdirectory
   - Reject directory (on failure) with Rejection-Reason added
4. **Updating** file headers with stage-specific metadata
5. **Logging** all operations with Joke-ID prefix
6. **Retrying** up to 2 times on processing errors
7. **Handling** both priority and main pipelines (priority first)

**No orchestration checks return codes**; stages perform all work autonomously.

---

## 12. Out of Scope

The following are explicitly **out of scope** for this project:

* Database integration and insertion
* What happens to files after manual review
* Manual reinjection procedures
* Priority pipeline routing logic (when files appear, process them)
* Log rotation (future feature)
* Performance optimization and scaling
* Monitoring dashboards and alerting
* Backup and recovery procedures
* Processing files in `08_ready_for_review/` (human reviewers handle this)

---

## 13. Performance Expectations

* **Expected Volume**: 1-10 jokes per day (low volume)
* **Batch Size**: 1 file per stage execution
* **Processing Time**: No specific requirements; optimize later as needed
* **Concurrency**: One cron job per stage; no parallel processing within stages
* **Scaling**: Future feature; start small and simple

---

## Appendix A: Sample Joke File from joke-extract.py

```
Title: Colorful Meal
Submitter: "'Thomas S. Ellsworth' tellswor@kcbx.net [good-clean-fun]" <good-clean-fun-noreply@yahoogroups.com>

Over dinner, I explained the health benefits of a colorful meal to my family. "The more colors, the more variety of nutrients," I told them. Pointing to our food, I asked, "How many different colors do you see?"

"Six," volunteered my daughter. "Seven if you count the burned parts."
```

**Note**: This file will be renamed to `<UUID>.txt` by the pipeline wrapper, which will also add Joke-ID, Source-Email-File, and Pipeline-Stage headers.

---

## Appendix B: search_tfidf.py Output Format

Example output (single line to stdout):

```
91 9278 A Meaningful New Year's Gesture
```

* First integer: **91** = match score (0-100)
* Remaining text: Details about matched joke (ignore)

Pipeline must parse the first integer and compare against DUPLICATE_THRESHOLD.

---

## Document Version History

* **v1.0** (2026-02-14): Initial specification
* **v1.1** (2026-02-14): Added external script details, Ollama configuration, valid categories, clarified metadata progression, removed database references, added retry logic, confidence thresholds, and performance expectations
