# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a joke submission pipeline that processes joke submissions from emails through multiple automated stages before reaching manual review. It's a file-based state machine that uses LLMs (via Ollama) and TF-IDF for duplicate detection.

## Commands

### Setup
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create pipeline directory structure
python3 setup_directories.py
```

### Testing
```bash
# Run all tests
python3 -m pytest tests/

# Run a specific test file
python3 -m pytest tests/test_file_utils.py

# Run a specific test function
python3 -m pytest tests/test_file_utils.py::test_parse_joke_file

# Run with verbose output
python3 -m pytest -v tests/

# Run with coverage
python3 -m pytest --cov=src
```

### Linting
```bash
# Lint a file with flake8
flake8 --append-config=flake8.ini stage_incoming.py

# Lint src/ folder
flake8 --append-config=flake8.ini src/
```

### Running Stages
Each stage processor can be run independently:
```bash
python3 stage_incoming.py
python3 stage_parsed.py
# etc.
```

### External Dependencies
- **Ollama**: Required for LLM operations. Must be running locally on port 11434 with the llama3 model
- **joke-extractor**: External script at `joke-extractor/joke-extract.py` for parsing email jokes
  - **Do not modify without explicit instructions**
- **jokematch2**: TF-IDF duplicate detection system
  - `jokematch2/build_tfidf.py`: Builds TF-IDF index
  - `jokematch2/search_tfidf.py`: Searches for similar jokes, returns format: `<score> <id> <title>`
  - **Do not modify without explicit instructions**

## Architecture

### File-Based State Machine
The pipeline is built around a file-based state machine where:
- Each joke is a single text file with a UUID filename
- Files move through stage directories as they're processed
- Two parallel pipelines exist: `pipeline-main/` and `pipeline-priority/` (priority processed first)
- All file operations use atomic writes via `tmp/` subdirectories

### Joke File Format
Each joke file has this structure:
```
Joke-ID: <uuid>
Title: <title>
Submitter: <email>
Pipeline-Stage: <stage_name>
[other headers...]

<joke content>
```

Headers and content are separated by a blank line. The `file_utils.py` module handles parsing and writing this format.

### Pipeline Stages
Jokes flow through 8 stages (in `config.py`):
1. **01_incoming** - Raw email files
2. **02_parsed** - Extracted jokes from emails via joke-extract.py
3. **03_deduped** - Duplicate checking via TF-IDF similarity
4. **04_clean_checked** - Cleanliness verification via LLM
5. **05_formatted** - Grammar/punctuation formatting via LLM
6. **06_categorized** - Category assignment via LLM
7. **07_titled** - Title assignment (if needed)
8. **08_ready_for_review** - Final manual review

Rejected jokes go to `50_rejected_*` directories (defined in `config.REJECTS`).

### Core Architecture Pattern: StageProcessor
All stages inherit from `StageProcessor` (in `stage_processor.py`), which provides:
- Automatic retry logic (2 retries = 3 total attempts, configured in `config.MAX_RETRIES`)
- Priority pipeline processing (processes `pipeline-priority/` before `pipeline-main/`)
- Atomic file operations using `atomic_write()` and `atomic_move()`
- Automatic logging with Joke-ID tracking
- Rejection handling with reason tracking

Subclasses only need to implement `process_file()` which returns:
```python
(success: bool, updated_headers: dict, updated_content: str, reject_reason: str)
```

### Atomic Operations
All file writes use the tmp/ subdirectory pattern (implemented in `file_utils.py`):
1. Write to `<dir>/tmp/<uuid>.txt`
2. Atomic rename to `<dir>/<filename>.txt`
3. This prevents partial writes and ensures consistency

### External Scripts Integration
The `external_scripts.py` module provides:
- `run_external_script()`: Safe execution with timeout and error handling
- `parse_tfidf_score()`: Parses output from search_tfidf.py (format: `<score> <id> <title>`)

### Configuration
`config.py` is the central configuration file containing:
- Directory paths for both pipelines
- Stage and reject directory names
- External script paths (JOKE_EXTRACTOR, BUILD_TFIDF, SEARCH_TFIDF)
- Thresholds (DUPLICATE_THRESHOLD, CLEANLINESS_MIN_CONFIDENCE, etc.)
- Ollama LLM configuration (model, API URL, parameters)
- Valid joke categories (VALID_CATEGORIES)
- Logging configuration

### Logging
The `logging_utils.py` module provides centralized logging:
- `setup_logging()`: Configures file and console logging
- `get_logger()`: Returns logger instance (auto-configures if needed)
- All logs go to `logs/pipeline.log`
- Joke-ID is automatically included in log messages for traceability

## Key Implementation Details

### Stage Implementations
- **stage_incoming.py**: Unique stage that processes EMAIL files (not joke files), calls joke-extract.py, may produce 0 or more jokes per email
- **stage_parsed.py**: Implements deduplication using TF-IDF via search_tfidf.py
- Other stages follow similar patterns using the StageProcessor base class

### Test Fixtures
Tests use mock external scripts:
- `tests/fixtures/mock_joke_extract.py`: Mocks joke-extractor
- `tests/fixtures/mock_search_tfidf.py`: Mocks TF-IDF search (outputs format expected by `parse_tfidf_score()`)

### Important Patterns
1. **Always use atomic operations**: Use `atomic_write()` and `atomic_move()` from file_utils.py, never write directly
2. **Parse with file_utils**: Always use `parse_joke_file()` and `write_joke_file()` for consistency
3. **Update Pipeline-Stage header**: When moving files between stages, update the Pipeline-Stage header
4. **Handle both pipelines**: Stage processors must handle both pipeline-main/ and pipeline-priority/
5. **Log with Joke-ID**: Always include Joke-ID in log messages for traceability

### Mock vs Real External Scripts
- Tests use mock scripts in `tests/fixtures/`
- Production uses real scripts: `joke-extractor/joke-extract.py`, `jokematch2/search_tfidf.py`
- The mock for search_tfidf.py MUST output the exact format: `<score> <id> <title>` that the real script outputs

## Code Style Guidelines

### Python Version and Encoding
- Use Python 3.11+
- All files must use strict UTF-8 encoding
- All scripts must have shebangs: `#!/usr/bin/env python3`
- Email files must be processed with ISO-8859-1 encoding (as specified in file_utils.py)

### Imports
Import order:
1. Standard library imports
2. Third-party imports
3. Local application imports

Guidelines:
- All imports at the top of the file
- Use absolute imports when possible
- Import individual modules, not wildcard imports (e.g., `from email import message_from_file` not `from email import *`)
- Remove unused imports
- Use `from typing import` for type hints

### Formatting
- **Indentation**: 2 spaces (no tabs)
- **Line length**: Maximum 88 characters (PEP8 + black)
- **Naming conventions**:
  - `snake_case` for functions, variables, attributes
  - `PascalCase` for classes
  - `UPPER_CASE` for constants
  - `_snake_case` for private methods (e.g., `_validate_headers`)
- No trailing whitespace
- Single blank lines to separate logical sections
- Double blank lines to separate top-level functions or classes

### Type Hints
- Always add type hints for function parameters and return values
- Use `List[T]`, `Dict[K, V]`, `Tuple[...]` from typing module
- Example:
  ```python
  def parse_joke_file(filepath: str) -> Tuple[Dict[str, str], str]:
  ```

### Logging
- **Use the `logging` module for all output, never `print()`**
- Use `get_logger()` from `logging_utils.py` to get logger instances
- All logs go to `logs/pipeline.log`
- Include Joke-ID in log messages for traceability

### Error Handling
- Use try-except blocks with specific exception types
- Create custom exceptions when appropriate
- Log errors using the logging module
- Provide informative error messages

### Documentation
- Write docstrings for all functions and classes (Google style)
- Include parameter descriptions and return values
- Document all public methods

### Best Practices
- Keep functions small and focused on single responsibility
- Use context managers (`with` statements) for resource management
- Include `__main__` guards for executable modules
- Write unit tests for all functions
- Validate inputs and handle edge cases
