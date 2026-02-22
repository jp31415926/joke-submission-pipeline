# Joke Submission Pipeline

This pipeline processes joke submissions from emails through multiple automated stages before reaching manual review. It's a file-based state machine that uses LLMs (via Ollama) and TF-IDF for duplicate detection.

## Quick Start

```bash
# Setup
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 setup_directories.py

# Run pipeline
python3 joke-pipeline.py

# Run tests
python3 -m pytest tests/
```

## Architecture

The pipeline follows a **batch-oriented, file-based state machine** approach with independent processing stages:

- **Dual pipelines**: `pipeline-priority/` and `pipeline-main/` (priority processed first)
- **Atomic operations**: All file moves use `tmp/` subdirectories to prevent corruption
- **Retry logic**: 2 retries (3 total attempts) on processing errors
- **LLM integration**: Uses Ollama (llama3 model) for cleanliness, formatting, and categorization
- **Low volume**: Designed for 1-10 jokes per day

## Pipeline Stages

Each joke progresses through these stages:

1. **01_incoming** - Extract jokes from email files using joke-extractor
   - Calls external `joke-extract.py` script
   - May produce 0 or more jokes per email
   - Generates UUID for each joke and initializes metadata

2. **02_parsed** - Duplicate detection using TF-IDF similarity
   - Calls external `search_tfidf.py` script
   - Rejects jokes with similarity score ≥ 70 (configurable)
   - Records duplicate score in metadata

3. **03_deduped** - Cleanliness verification using LLM
   - Checks if joke is clean and appropriate
   - Requires confidence ≥ 70 (configurable)
   - Rejects inappropriate content

4. **04_clean_checked** - Grammar and punctuation formatting using LLM
   - Improves joke formatting and grammar
   - Updates joke content with formatted version
   - Maintains original meaning

5. **05_formatted** - Category assignment using LLM
   - Assigns 1-10 categories from predefined list
   - Validates categories against `VALID_CATEGORIES` in joke_categories.py
   - Requires confidence ≥ 70 (configurable)

6. **06_categorized** - Title generation (if needed) and final validation
   - Generates title for jokes with blank titles
   - Validates all required fields are present
   - Ensures content length > 10 characters
   - Confirms Cleanliness-Status and Format-Status are PASS

7. **08_ready_for_review** - Holding area for manual review
   - All automated processing complete
   - Ready for human reviewer approval
   - Manual review process is out of scope for this project

### Rejection Directories

Failed jokes move to appropriate rejection directories:
- `50_rejected_parse` - joke-extract.py failed or no jokes found
- `51_rejected_duplicate` - Duplicate detected (similarity ≥ threshold)
- `52_rejected_cleanliness` - Failed cleanliness check
- `53_rejected_format` - Failed formatting
- `54_rejected_category` - Invalid or missing categories
- `55_rejected_titled` - Failed title generation or final validation

## File Format

Each joke is a single text file named `<UUID>.txt` with this structure:

```
Joke-ID: 550e8400-e29b-41d4-a716-446655440000
Title: Why the Chicken Crossed the Road
Submitter: "John Doe" <john@example.com>
Source-Email-File: 1700000000.M1234.mailbox
Pipeline-Stage: 06_categorized
Duplicate-Score: 42
Duplicate-Threshold: 70
Cleanliness-Status: PASS
Cleanliness-Confidence: 85
Format-Status: PASS
Format-Confidence: 92
Categories: Animals, Wordplay
Rejection-Reason:

Why did the chicken cross the road?
To get to the other side!
```

Headers and content are separated by a blank line.

## Requirements

### System Requirements
- Unix/Linux machine
- Python 3.11+
- Local Ollama instance with llama3 model running on port 11434

### External Dependencies
- **Ollama**: LLM operations (http://localhost:11434)
- **joke-extractor**: External script at `joke-extractor/joke-extract.py`
  - Parses jokes from email files
  - **Do not modify without explicit instructions**
- **jokematch2**: TF-IDF duplicate detection system
  - `jokematch2/build_tfidf.py` - Builds TF-IDF index
  - `jokematch2/search_tfidf.py` - Searches for similar jokes
  - **Do not modify without explicit instructions**

## Usage

### Running the Full Pipeline
```bash
# Process both main and priority pipelines
python3 joke-pipeline.py

# Process only main pipeline
python3 joke-pipeline.py --pipeline main

# Process only priority pipeline
python3 joke-pipeline.py --pipeline priority
```

### Running Individual Stages
```bash
# Run specific stage only
python3 joke-pipeline.py --stage parsed
python3 joke-pipeline.py --stage deduped

# Or run stage script directly
python3 stage_incoming.py
python3 stage_parsed.py
```

### Running with Verbose Logging
```bash
python3 joke-pipeline.py --verbose
```

## Testing

```bash
# Run all tests
python3 -m pytest tests/

# Run with verbose output
python3 -m pytest tests/ -v

# Run specific test file
python3 -m pytest tests/test_file_utils.py

# Run with coverage
python3 -m pytest --cov=src
```

## Configuration

All configuration is in `config.py`:
- Pipeline directories
- External script paths
- Duplicate threshold (default: 70)
- LLM confidence thresholds (default: 70)
- Ollama API settings
- Valid joke categories
- Retry settings (default: 2 retries = 3 total attempts)
- Logging configuration

## Documentation

For detailed implementation information, see:
- **CLAUDE.md** - Comprehensive implementation guide (primary reference)
- **spec3.md** - Original project specification
- **config.py** - All configurable settings

## Logging

All logs are written to `logs/pipeline.log` with:
- Timestamps
- Log levels (INFO, WARNING, ERROR)
- Joke-ID prefixes for traceability
- Stage processing details