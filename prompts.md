# Joke Submission Pipeline - Implementation Prompts

This document contains step-by-step prompts for implementing the joke submission pipeline. Each prompt builds on the previous ones and should be executed in order.

---

## Step 1: Project Structure & Configuration

```
Create the foundational project structure and configuration management for the joke submission pipeline.

Requirements:
1. Create a config.py file with the following structure:
   - PIPELINE_MAIN and PIPELINE_PRIORITY directory paths
   - STAGES dictionary mapping stage names to directory names (incoming, parsed, deduped, clean_checked, formatted, categorized, titled, ready_for_review)
   - REJECTS dictionary mapping rejection types to directory names (parse, duplicate, cleanliness, format, category, titled)
   - Script paths: JOKE_EXTRACTOR, BUILD_TFIDF, SEARCH_TFIDF
   - Thresholds: DUPLICATE_THRESHOLD (default 70), CLEANLINESS_MIN_CONFIDENCE (70), CATEGORIZATION_MIN_CONFIDENCE (70)
   - ollama_config dictionary with all Ollama settings as specified in the spec
   - VALID_CATEGORIES list with all categories from the spec
   - MAX_CATEGORIES_PER_JOKE (3)
   - LOG_DIR and LOG_LEVEL
   - MAX_RETRIES (2)

2. Create a setup_directories.py script that:
   - Reads paths from config.py
   - Creates all pipeline directories for both main and priority pipelines
   - Creates tmp/ subdirectories in each stage directory
   - Creates log directory
   - Handles existing directories gracefully

3. Create tests/test_config.py that:
   - Verifies config.py imports successfully
   - Checks all required constants are present
   - Validates data types of configuration values
   - Tests that VALID_CATEGORIES is a non-empty list
   - Verifies ollama_config has all required keys

4. Create tests/test_setup_directories.py that:
   - Tests directory creation in a temporary location
   - Verifies all stage directories are created
   - Verifies tmp/ subdirectories exist
   - Tests idempotency (running twice doesn't cause errors)

Implementation notes:
- Use os.path.join for all path construction
- Make paths configurable but provide sensible defaults
- Include docstrings for all functions
- Follow PEP 8 style guidelines

Testing approach:
- Run tests with pytest
- Use real filesystem operations in a temp directory
- Verify all directories exist after setup
- Clean up test directories after tests complete

Deliverables:
- config.py
- setup_directories.py
- tests/test_config.py
- tests/test_setup_directories.py
- All tests passing
```

---

## Step 2: File Metadata Parser & Writer

```
Implement utilities to parse and write joke file headers and content.

Build on: Step 1 (config.py exists)

Requirements:
1. Create file_utils.py with the following functions:

   parse_joke_file(filepath):
   - Read the file at filepath
   - Parse headers (key: value format) until blank line
   - Return tuple: (headers_dict, content_string)
   - Handle files with no headers (joke-extract.py format)
   - Handle UTF-8 encoding
   - Raise clear exceptions for malformed files

   write_joke_file(filepath, headers_dict, content):
   - Write headers in "Key: Value" format, one per line
   - Add blank line separator
   - Write content
   - Use UTF-8 encoding
   - Ensure trailing newline

   validate_headers(headers_dict, required_fields):
   - Check that all fields in required_fields list are present in headers_dict
   - Check that required fields are not empty strings
   - Return tuple: (is_valid, missing_fields_list)

2. Create tests/test_file_utils.py that:
   - Tests parsing joke-extract.py format (Title and Submitter only)
   - Tests parsing full pipeline format (all headers)
   - Tests parsing file with blank Title field
   - Tests round-trip: write then read produces identical data
   - Tests validation with all required fields present
   - Tests validation with missing required fields
   - Tests validation with empty string values
   - Uses real sample files in tests/fixtures/

3. Create tests/fixtures/ directory with sample joke files:
   - sample_extract_output.txt (joke-extract.py format)
   - sample_full_headers.txt (complete pipeline format)
   - sample_blank_title.txt (Title field exists but is blank)

Implementation notes:
- Handle both Windows (\r\n) and Unix (\n) line endings
- Strip whitespace from header keys and values
- Preserve original content exactly (including whitespace)
- Use clear error messages

Testing approach:
- Create real files in fixtures directory
- Test with actual file I/O
- Verify exact content preservation
- Test edge cases (blank lines in content, special characters)

Deliverables:
- file_utils.py with parse_joke_file, write_joke_file, validate_headers
- tests/test_file_utils.py
- tests/fixtures/ with sample files
- All tests passing
```

---

## Step 3: Atomic File Operations

```
Implement safe atomic file operations using tmp/ subdirectories to prevent partial file writes.

Build on: Step 2 (file_utils.py with parse and write functions)

Requirements:
1. Add to file_utils.py:

   atomic_write(target_path, headers_dict, content):
   - Extract directory from target_path
   - Create tmp/ subdirectory if it doesn't exist
   - Generate temporary filename in tmp/ (e.g., tmp/<uuid>.txt)
   - Write file to temporary location using write_joke_file
   - Move temporary file to target_path using os.rename (atomic on same filesystem)
   - Return True on success, raise exception on failure

   atomic_move(source_path, dest_dir):
   - Verify source_path exists
   - Extract filename from source_path
   - Create dest_dir if it doesn't exist
   - Create tmp/ subdirectory in dest_dir if it doesn't exist
   - Copy source to dest_dir/tmp/<filename> (NOT using os.rename yet)
   - Move from dest_dir/tmp/<filename> to dest_dir/<filename> using os.rename
   - Delete source file only after successful move
   - Return destination path on success

   safe_cleanup(filepath):
   - Check if filepath exists
   - If exists, delete it
   - Log deletion (use print for now, proper logging in Step 4)
   - Handle errors gracefully (don't raise if file doesn't exist)

2. Expand tests/test_file_utils.py:
   - Test atomic_write creates file in tmp/ first
   - Test atomic_write final file appears only after completion
   - Test atomic_move uses tmp/ subdirectory
   - Test atomic_move source file deleted only after success
   - Test safe_cleanup removes existing file
   - Test safe_cleanup handles non-existent file
   - Test partial failure scenarios (simulate disk full, permission errors)
   - Use real filesystem in temporary test directory

Implementation notes:
- Use uuid.uuid4() for temporary filenames
- Ensure tmp/ directory creation is atomic (use os.makedirs with exist_ok=True)
- Use shutil.copy2 for initial copy (preserves metadata)
- os.rename is atomic on the same filesystem
- Handle cross-filesystem moves (source and dest on different mounts)

Testing approach:
- Use tempfile.TemporaryDirectory for test directories
- Verify intermediate files in tmp/ during operation
- Check final location only has file after completion
- Test with real files (no mocking)
- Verify no partial files left on failure

Deliverables:
- Updated file_utils.py with atomic_write, atomic_move, safe_cleanup
- Updated tests/test_file_utils.py with new tests
- All tests passing
```

---

## Step 4: Logging Infrastructure

```
Implement centralized logging with Joke-ID prefix support.

Build on: Step 1 (config.py with LOG_DIR and LOG_LEVEL)

Requirements:
1. Create logging_utils.py with:

   setup_logging(log_dir, log_level):
   - Create log_dir if it doesn't exist
   - Configure Python logging with:
     * File handler: writes to log_dir/pipeline.log
     * Console handler: writes to stdout
     * Format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
     * Level from log_level parameter (e.g., "INFO", "DEBUG")
   - Return configured logger

   get_logger(name):
   - Return logger instance for given name
   - If logging not configured, configure with defaults from config.py

   log_with_joke_id(logger, level, joke_id, message):
   - Format message with Joke-ID prefix: "[Joke-ID: {joke_id}] {message}"
   - Log at specified level (DEBUG, INFO, WARNING, ERROR)
   - Handle None joke_id gracefully (log without prefix)

2. Create tests/test_logging_utils.py:
   - Test setup_logging creates log directory
   - Test setup_logging creates log file
   - Test log messages written to file
   - Test log messages written to console
   - Test log_with_joke_id includes Joke-ID prefix
   - Test log_with_joke_id handles None joke_id
   - Test different log levels (DEBUG, INFO, WARNING, ERROR)
   - Use real log files in temporary directory

Implementation notes:
- Use Python's logging module
- Support rotation in future (but not required now)
- Use logging.Formatter for consistent formatting
- Clear separation between setup and usage

Testing approach:
- Create temporary log directory for tests
- Write logs and verify file contents
- Capture stdout to verify console output
- Test with real logging calls (no mocking)
- Clean up log files after tests

Deliverables:
- logging_utils.py
- tests/test_logging_utils.py
- All tests passing
```

---

## Step 5: Stage Processor Base Class

```
Create an abstract base class for all pipeline stage processors with retry logic and priority handling.

Build on: Steps 2, 3, 4 (file_utils, logging_utils exist)

Requirements:
1. Create stage_processor.py with:

   StageProcessor (abstract base class):
   - Constructor accepts:
     * stage_name: string (e.g., "parsed")
     * input_stage: string (e.g., "incoming")
     * output_stage: string (e.g., "deduped")
     * reject_stage: string (e.g., "rejected_duplicate")
     * config: config module
   
   - Abstract method process_file(filepath, headers, content):
     * Must be implemented by subclasses
     * Returns tuple: (success: bool, updated_headers: dict, updated_content: str, reject_reason: str)
     * reject_reason only used if success is False
   
   - Method run():
     * Check priority pipeline first (config.PIPELINE_PRIORITY)
     * Then check main pipeline (config.PIPELINE_MAIN)
     * For each pipeline, process all files in input stage directory
     * Skip tmp/ subdirectories
     * Process one file at a time
     * Log start and completion of each pipeline
   
   - Method _process_with_retry(filepath):
     * Read file using file_utils.parse_joke_file
     * Call process_file() (the abstract method)
     * On exception, retry up to MAX_RETRIES times
     * On success, call _move_to_output
     * On final failure, call _move_to_reject
     * Log each attempt with Joke-ID
   
   - Method _move_to_output(filepath, headers, content):
     * Update Pipeline-Stage in headers to output_stage
     * Write file using atomic_write
     * Move to output directory using atomic_move
     * Log success with Joke-ID
   
   - Method _move_to_reject(filepath, headers, content, reason):
     * Update Pipeline-Stage in headers to reject_stage
     * Add Rejection-Reason to headers
     * Write file using atomic_write
     * Move to reject directory using atomic_move
     * Log rejection with Joke-ID and reason

2. Create tests/test_stage_processor.py:
   - Create MockStageProcessor subclass for testing
     * Implements process_file to return success
     * Configurable to fail N times then succeed (for retry testing)
   
   - Test priority pipeline processed before main
   - Test retry logic (fail twice, succeed on third attempt)
   - Test rejection after max retries exceeded
   - Test metadata updated correctly (Pipeline-Stage)
   - Test Rejection-Reason added on failure
   - Test files moved to correct directories
   - Use real files and directories in temp location

Implementation notes:
- Use abc module for abstract base class
- Import config module, don't instantiate it
- Extensive logging at each step
- Clear separation of concerns (processing vs file movement)
- Use Joke-ID from headers for all logging

Testing approach:
- Create temporary pipeline directories
- Create sample files in input stage
- Run processor and verify files moved
- Check metadata updates
- Verify retry logic with controlled failures
- Use real file operations

Deliverables:
- stage_processor.py with StageProcessor abstract base class
- tests/test_stage_processor.py with MockStageProcessor
- All tests passing
```

---

## Step 6: UUID Generation & Metadata Initialization

```
Add utilities for generating Joke-IDs and initializing file metadata.

Build on: Step 2 (file_utils.py exists)

Requirements:
1. Add to file_utils.py:

   generate_joke_id():
   - Generate UUID using uuid.uuid4()
   - Return as string
   - Format: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"

   initialize_metadata(headers, email_filename, stage_name):
   - Add Joke-ID (if not present) using generate_joke_id()
   - Add Source-Email-File with email_filename value
   - Add Pipeline-Stage with stage_name value
   - Preserve all existing headers
   - Return updated headers dictionary

2. Expand tests/test_file_utils.py:
   - Test generate_joke_id returns valid UUID format
   - Test generate_joke_id creates unique IDs (generate 100, verify all unique)
   - Test initialize_metadata adds Joke-ID
   - Test initialize_metadata adds Source-Email-File
   - Test initialize_metadata adds Pipeline-Stage
   - Test initialize_metadata preserves existing headers (Title, Submitter)
   - Test initialize_metadata doesn't overwrite existing Joke-ID

Implementation notes:
- Use Python's uuid module
- Validate UUID format (8-4-4-4-12 hex digits with hyphens)
- Don't overwrite existing Joke-ID (critical for idempotency)
- Preserve all existing metadata

Testing approach:
- Generate multiple UUIDs and verify uniqueness
- Test with existing headers (from joke-extract.py)
- Verify no data loss
- Test with empty headers dictionary

Deliverables:
- Updated file_utils.py with generate_joke_id, initialize_metadata
- Updated tests/test_file_utils.py
- All tests passing
```

---

## Step 7: External Script Integration Utilities

```
Create utilities for safely calling external scripts and parsing their output.

Build on: Step 4 (logging_utils exists)

Requirements:
1. Create external_scripts.py with:

   run_external_script(script_path, args, timeout=60):
   - Verify script_path exists and is executable
   - Build command: [script_path] + args
   - Execute using subprocess.run with:
     * capture_output=True
     * text=True
     * timeout=timeout
     * check=False (we'll handle return codes ourselves)
   - Return tuple: (return_code, stdout, stderr)
   - Log command execution and result
   - Handle timeout exceptions
   - Handle permission errors

   parse_tfidf_score(output):
   - Parse search_tfidf.py output format: "91 9278 A Meaningful New Year's Gesture"
   - Extract first integer (the score)
   - Return integer score (0-100)
   - Raise ValueError if output doesn't match expected format
   - Handle empty output gracefully

2. Create tests/test_external_scripts.py:
   - Test run_external_script with simple command (e.g., /bin/echo)
   - Test return code capture
   - Test stdout capture
   - Test stderr capture
   - Test timeout handling (use sleep command)
   - Test parse_tfidf_score with valid output
   - Test parse_tfidf_score with invalid output
   - Test parse_tfidf_score with empty output
   - Create mock search_tfidf.py script for testing (in tests/fixtures/)

3. Create tests/fixtures/mock_search_tfidf.py:
   - Simple script that prints "42 1234 Test Joke Title"
   - Make executable (chmod +x)
   - Use for integration testing

Implementation notes:
- Use subprocess.run (Python 3.5+)
- Set reasonable default timeout (60 seconds)
- Log all external script calls
- Handle encoding issues (text=True uses default encoding)
- Raise clear exceptions with context

Testing approach:
- Use real subprocess calls (no mocking)
- Test with actual shell commands
- Test timeout with sleep command
- Verify output parsing with known inputs
- Test error conditions

Deliverables:
- external_scripts.py
- tests/test_external_scripts.py
- tests/fixtures/mock_search_tfidf.py
- All tests passing
```

---

## Step 8: Stage 01 - Incoming (Email Extraction)

```
Implement the first pipeline stage that processes emails through joke-extract.py.

Build on: Steps 5, 6, 7 (StageProcessor, UUID generation, external scripts)

Requirements:
1. Create stage_incoming.py with:

   IncomingProcessor(StageProcessor):
   - Constructor sets stage_name="incoming", output_stage="parsed", reject_stage="rejected_parse"
   
   - Implement process_file(filepath, headers, content):
     * Extract email filename from filepath
     * Create temporary success and fail directories
     * Call joke-extract.py: run_external_script(config.JOKE_EXTRACTOR, [filepath, success_dir, fail_dir])
     * Check return code (0 = success)
     * For each file in success_dir:
       - Read extracted joke
       - Generate unique Joke-ID
       - Initialize metadata with initialize_metadata
       - Save to output directory
     * If return code != 0 or no files extracted:
       - Return (False, headers, content, "joke-extract.py failed" or appropriate reason)
     * Clean up temporary directories
     * Return (True, final_headers, final_content, "")
   
   - Note: This stage processes EMAIL files, not joke files
   - Each email may produce 0 or more joke files
   - Each joke gets its own UUID

2. Create tests/test_stage_incoming.py:
   - Create mock email files in tests/fixtures/emails/
   - Create mock joke-extract.py that:
     * Takes email file and outputs sample joke to success_dir
     * Simulates both success and failure
   - Test processing email with single joke
   - Test processing email with multiple jokes
   - Test processing email with no jokes (fail case)
   - Test joke-extract.py failure (non-zero return code)
   - Verify UUID generation for each joke
   - Verify metadata initialization
   - Verify files moved to parsed/ directory
   - Test with real temp directories

3. Create tests/fixtures/emails/:
   - sample_single_joke.eml
   - sample_multiple_jokes.eml
   - sample_no_jokes.eml

Implementation notes:
- Handle multiple jokes from single email
- Each joke gets unique UUID
- Preserve Title and Submitter from joke-extract.py
- Clean up temporary directories even on failure
- Log each joke extraction

Testing approach:
- Use real subprocess to call mock joke-extract.py
- Verify file creation and movement
- Check metadata in output files
- Test with actual filesystem operations

Deliverables:
- stage_incoming.py
- tests/test_stage_incoming.py
- tests/fixtures/emails/ with sample files
- Mock joke-extract.py for testing
- All tests passing
```

---

## Step 9: Stage 02 - Parsed (Duplicate Detection)

```
Implement duplicate detection stage using search_tfidf.py.

Build on: Steps 5, 7 (StageProcessor, external scripts)

Requirements:
1. Create stage_parsed.py with:

   ParsedProcessor(StageProcessor):
   - Constructor sets stage_name="parsed", output_stage="deduped", reject_stage="rejected_duplicate"
   
   - Implement process_file(filepath, headers, content):
     * Write content to temporary file for search_tfidf.py
     * Call search_tfidf.py: run_external_script(config.SEARCH_TFIDF, [temp_file])
     * Parse score using parse_tfidf_score(stdout)
     * Add Duplicate-Score to headers (integer)
     * Add Duplicate-Threshold to headers (from config)
     * Compare score to config.DUPLICATE_THRESHOLD
     * If score >= threshold:
       - Return (False, headers, content, f"Duplicate score {score} >= threshold {threshold}")
     * If score < threshold:
       - Return (True, headers, content, "")
     * Handle search_tfidf.py errors (return code != 0)
     * Clean up temporary file

2. Create tests/test_stage_parsed.py:
   - Create mock search_tfidf.py that returns configurable scores
   - Test with score below threshold (should pass)
   - Test with score at threshold (should fail)
   - Test with score above threshold (should fail)
   - Test metadata updates (Duplicate-Score, Duplicate-Threshold)
   - Test search_tfidf.py failure handling
   - Test with real files in temp directories
   - Verify files moved to deduped/ or rejected_duplicate/

3. Update tests/fixtures/mock_search_tfidf.py:
   - Accept environment variable MOCK_SCORE to return specific scores
   - Default to score 30 (below threshold)

Implementation notes:
- Create temporary file for search_tfidf.py input
- Parse only the first integer from output
- Use >= for threshold comparison (duplicate if score meets or exceeds threshold)
- Log duplicate score for every file
- Clean up temporary files

Testing approach:
- Use mock search_tfidf.py with controlled output
- Test threshold edge cases (exactly at threshold)
- Verify metadata in output files
- Test error handling

Deliverables:
- stage_parsed.py
- tests/test_stage_parsed.py
- Updated tests/fixtures/mock_search_tfidf.py
- All tests passing
```

---

## Step 10: Ollama LLM Integration Utility

```
Create a reusable client for interacting with Ollama API.

Build on: Step 1 (config.py with ollama_config), Step 4 (logging)

Requirements:
1. Create ollama_client.py with:

   OllamaClient:
   - Constructor accepts ollama_config dictionary from config
   - Store API URL, model name, and options
   
   - Method generate(system_prompt, user_prompt):
     * Build request body with:
       - model: from config
       - prompt: user_prompt
       - system: system_prompt
       - stream: False (we want complete responses)
       - options: from config
     * POST to ollama_api_url
     * Parse JSON response
     * Extract response text from response['response']
     * Return response text
     * Handle network errors, timeout, invalid JSON
     * Log request and response (truncated for readability)
   
   - Method parse_structured_response(response_text, expected_keys):
     * Attempt to parse response as JSON
     * If not JSON, look for key-value pairs in format "Key: Value"
     * Return dictionary with extracted values
     * Handle missing keys gracefully
   
   - Method extract_confidence(response_dict):
     * Look for confidence score in response
     * Try keys: "confidence", "Confidence", "score"
     * Parse as integer (0-100)
     * Return integer or None if not found
     * Handle non-integer values

2. Create tests/test_ollama_client.py:
   - Test generate() with mock Ollama server (use requests_mock or similar)
   - Test successful response parsing
   - Test network error handling
   - Test timeout handling
   - Test parse_structured_response with JSON response
   - Test parse_structured_response with key-value format
   - Test extract_confidence with various formats
   - If real Ollama available, test with actual API call

3. Optional: Create tests/mock_ollama_server.py:
   - Simple Flask server that mimics Ollama API
   - Returns canned responses for testing
   - Use only if real Ollama not available for tests

Implementation notes:
- Use requests library for HTTP calls
- Set reasonable timeout (30 seconds)
- Handle rate limiting (429 responses)
- Parse both JSON and text responses
- Log all API calls for debugging

Testing approach:
- Prefer testing with real Ollama if available
- Use mock server for CI/CD environments
- Test error conditions thoroughly
- Verify confidence score parsing with various inputs

Deliverables:
- ollama_client.py
- tests/test_ollama_client.py
- (Optional) tests/mock_ollama_server.py
- All tests passing
```

---

## Step 11: Stage 03 - Deduped (Cleanliness Check)

```
Implement cleanliness check stage using Ollama LLM.

Build on: Steps 5, 10 (StageProcessor, OllamaClient)

Requirements:
1. Create stage_deduped.py with:

   DedupedProcessor(StageProcessor):
   - Constructor:
     * Sets stage_name="deduped", output_stage="clean_checked", reject_stage="rejected_cleanliness"
     * Initializes OllamaClient with config.ollama_config
   
   - Implement process_file(filepath, headers, content):
     * Construct system prompt: "You are a content moderator evaluating jokes for appropriateness."
     * Construct user prompt:
       """
       Evaluate this joke for cleanliness and appropriateness:
       
       {content}
       
       Determine if this joke is:
       - Clean (no profanity, sexual content, or offensive material)
       - Appropriate for general audiences
       
       Respond with:
       Status: PASS or FAIL
       Confidence: <0-100 integer>
       Reason: <brief explanation>
       """
     * Call ollama_client.generate(system_prompt, user_prompt)
     * Parse response for Status, Confidence, Reason
     * Add Cleanliness-Status to headers (PASS or FAIL)
     * Add Cleanliness-Confidence to headers (integer 0-100)
     * If Status is FAIL:
       - Return (False, headers, content, f"Cleanliness check failed: {reason}")
     * If Confidence < config.CLEANLINESS_MIN_CONFIDENCE:
       - Return (False, headers, content, f"Confidence {confidence} below minimum {min}")
     * If Status is PASS and Confidence >= minimum:
       - Return (True, headers, content, "")
     * Handle LLM errors (return failure)

2. Create tests/test_stage_deduped.py:
   - Test with clean joke (should pass)
   - Test with questionable joke (may fail)
   - Test with high confidence (should pass)
   - Test with low confidence (should fail even if status is PASS)
   - Test metadata updates (Cleanliness-Status, Cleanliness-Confidence)
   - Test LLM error handling
   - Test with real Ollama if available
   - Verify files moved to correct directories

3. Create tests/fixtures/jokes/:
   - clean_joke.txt (definitely clean)
   - questionable_joke.txt (borderline)

Implementation notes:
- Clear, specific prompts to LLM
- Parse responses robustly (handle variations)
- Enforce confidence threshold strictly
- Log LLM responses for debugging
- Handle LLM failures gracefully

Testing approach:
- Test with real Ollama if available
- Use mock responses if Ollama not available
- Verify metadata in output files
- Test threshold enforcement
- Test various joke content

Deliverables:
- stage_deduped.py
- tests/test_stage_deduped.py
- tests/fixtures/jokes/ with sample jokes
- All tests passing
```

---

## Step 12: Stage 04 - Clean Checked (Formatting)

```
Implement formatting stage to improve joke grammar and punctuation.

Build on: Steps 5, 10 (StageProcessor, OllamaClient)

Requirements:
1. Create stage_clean_checked.py with:

   CleanCheckedProcessor(StageProcessor):
   - Constructor:
     * Sets stage_name="clean_checked", output_stage="formatted", reject_stage="rejected_format"
     * Initializes OllamaClient
   
   - Implement process_file(filepath, headers, content):
     * Construct system prompt: "You are an editor improving joke formatting and grammar."
     * Construct user prompt:
       """
       Improve the grammar, punctuation, and formatting of this joke while preserving its meaning and humor:
       
       {content}
       
       Respond with:
       Formatted-Joke: <the improved joke text>
       Confidence: <0-100 integer indicating quality of original>
       Changes: <brief description of changes made>
       """
     * Call ollama_client.generate(system_prompt, user_prompt)
     * Parse response for Formatted-Joke, Confidence, Changes
     * Add Format-Status: PASS to headers
     * Add Format-Confidence to headers (integer)
     * If Confidence < config.CATEGORIZATION_MIN_CONFIDENCE:
       - Return (False, headers, content, f"Format confidence {confidence} too low")
     * Update content with formatted joke text
     * Return (True, headers, formatted_content, "")
     * Handle LLM errors

2. Create tests/test_stage_clean_checked.py:
   - Test with well-formatted joke (minimal changes)
   - Test with poorly formatted joke (significant improvements)
   - Test confidence threshold enforcement
   - Test content update (formatted version replaces original)
   - Test metadata updates
   - Test with real Ollama if available
   - Verify formatted content in output files

3. Add to tests/fixtures/jokes/:
   - poorly_formatted_joke.txt (needs improvement)
   - well_formatted_joke.txt (already good)

Implementation notes:
- Preserve joke content and humor
- Update content in file, not just metadata
- Log changes made by LLM
- Handle cases where LLM doesn't follow format
- Confidence reflects quality of ORIGINAL, not formatted version

Testing approach:
- Compare original and formatted content
- Verify content actually updated
- Test with various formatting issues
- Verify metadata updates

Deliverables:
- stage_clean_checked.py
- tests/test_stage_clean_checked.py
- Updated tests/fixtures/jokes/
- All tests passing
```

---

## Step 13: Stage 05 - Formatted (Categorization)

```
Implement categorization stage to assign 1-3 categories to jokes.

Build on: Steps 5, 10 (StageProcessor, OllamaClient)

Requirements:
1. Create stage_formatted.py with:

   FormattedProcessor(StageProcessor):
   - Constructor:
     * Sets stage_name="formatted", output_stage="categorized", reject_stage="rejected_category"
     * Initializes OllamaClient
   
   - Implement process_file(filepath, headers, content):
     * Construct system prompt: "You are a joke categorization expert."
     * Construct user prompt:
       """
       Categorize this joke into 1-3 categories from this list:
       {', '.join(config.VALID_CATEGORIES)}
       
       Joke:
       {content}
       
       Respond with:
       Categories: <comma-separated list of 1-3 categories>
       Confidence: <0-100 integer>
       Reasoning: <brief explanation>
       """
     * Call ollama_client.generate(system_prompt, user_prompt)
     * Parse response for Categories, Confidence, Reasoning
     * Validate categories against config.VALID_CATEGORIES
     * Verify 1-3 categories (not more, not less)
     * Add Categories to headers (comma-separated string)
     * Add Category-Confidence to headers (integer)
     * If invalid categories or count wrong:
       - Return (False, headers, content, f"Invalid categories: {reason}")
     * If Confidence < config.CATEGORIZATION_MIN_CONFIDENCE:
       - Return (False, headers, content, f"Confidence {confidence} too low")
     * Return (True, headers, content, "")

2. Create tests/test_stage_formatted.py:
   - Test with joke matching 1 category
   - Test with joke matching 2 categories
   - Test with joke matching 3 categories
   - Test with invalid category (should fail)
   - Test with too many categories (should fail)
   - Test with too few categories (should fail)
   - Test confidence threshold
   - Test metadata updates
   - Test with real Ollama if available
   - Verify category validation

3. Add to tests/fixtures/jokes/:
   - pun_joke.txt (Puns category)
   - dad_joke.txt (Dad Jokes category)
   - animal_pun.txt (Animals + Puns categories)

Implementation notes:
- Strict category validation
- Enforce 1-3 category limit from config
- Case-insensitive category matching
- Log categorization results
- Handle LLM not following format

Testing approach:
- Test with various joke types
- Verify category validation
- Test edge cases (exactly 1, exactly 3)
- Ensure only valid categories accepted

Deliverables:
- stage_formatted.py
- tests/test_stage_formatted.py
- Updated tests/fixtures/jokes/
- All tests passing
```

---

## Step 14: Stage 06/07 - Categorized/Titled (Title Generation & Final Validation)

```
Implement title generation for jokes with blank titles and final validation before ready-for-review.

Build on: Steps 5, 10 (StageProcessor, OllamaClient)

Requirements:
1. Create stage_categorized.py with:

   CategorizedProcessor(StageProcessor):
   - Constructor:
     * Sets stage_name="categorized", output_stage="ready_for_review", reject_stage="rejected_titled"
     * Initializes OllamaClient
   
   - Implement process_file(filepath, headers, content):
     * Check if Title field exists and is not blank
     * If Title is blank or missing:
       - Construct system prompt: "You are a creative title writer for jokes."
       - Construct user prompt:
         """
         Create a short, catchy title for this joke:
         
         {content}
         
         Categories: {headers.get('Categories', 'Unknown')}
         
         Respond with:
         Title: <a short, engaging title>
         Confidence: <0-100 integer>
         """
       - Call ollama_client.generate(system_prompt, user_prompt)
       - Parse response for Title, Confidence
       - Update Title in headers
       - If Confidence < 70:
         * Return (False, headers, content, "Title generation confidence too low")
     * Perform final validation:
       - Required fields: Joke-ID, Title, Submitter, Source-Email-File, Pipeline-Stage, Categories
       - Required fields must not be blank
       - Cleanliness-Status must be PASS
       - Format-Status must be PASS
       - Content must be > 10 characters
     * If validation fails:
       - Return (False, headers, content, f"Validation failed: {specific_failures}")
     * If all validations pass:
       - Return (True, headers, content, "")

2. Create tests/test_stage_categorized.py:
   - Test with blank title (should generate)
   - Test with existing title (should preserve)
   - Test title generation
   - Test final validation with all fields present
   - Test final validation with missing Joke-ID (should fail)
   - Test final validation with blank Title (should fail)
   - Test final validation with short content (should fail)
   - Test final validation with Cleanliness-Status FAIL (should fail)
   - Test with real Ollama if available
   - Verify complete jokes reach ready_for_review/

3. Create comprehensive test fixture:
   - tests/fixtures/jokes/complete_joke.txt (all fields, should pass)
   - tests/fixtures/jokes/blank_title_joke.txt (needs title generation)
   - tests/fixtures/jokes/incomplete_joke.txt (missing required fields)

Implementation notes:
- Only generate title if blank
- Preserve existing titles
- Comprehensive validation before ready-for-review
- Specific error messages for each validation failure
- Log validation results

Testing approach:
- Test title generation separately
- Test validation separately
- Test complete flow
- Verify all required fields
- Test various failure scenarios

Deliverables:
- stage_categorized.py
- tests/test_stage_categorized.py
- tests/fixtures/jokes/ with validation test cases
- All tests passing
```

---

## Step 15: Main Orchestration Script

```
Create the main pipeline runner that executes all stages in sequence.

Build on: Steps 8-14 (all stage processors implemented)

Requirements:
1. Create joke-pipeline.py with:

   Main script structure:
   - Import all stage processors
   - Import config, logging_utils
   - Setup logging using config.LOG_DIR and config.LOG_LEVEL
   
   - Function run_pipeline(pipeline_type="both"):
     * pipeline_type can be "main", "priority", or "both"
     * If "both" or "priority", instantiate and run all stages for priority pipeline
     * If "both" or "main", instantiate and run all stages for main pipeline
     * Stages in order:
       1. IncomingProcessor
       2. ParsedProcessor
       3. DedupedProcessor
       4. CleanCheckedProcessor
       5. FormattedProcessor
       6. CategorizedProcessor
     * Log pipeline start and completion
     * Log summary statistics (files processed, rejected, succeeded)
   
   - Command-line interface:
     * --pipeline: "main", "priority", or "both" (default: "both")
     * --stage: Run specific stage only (optional)
     * --verbose: Enable DEBUG logging
     * --help: Show usage
   
   - Main execution:
     * Parse arguments
     * Setup logging
     * Run pipeline
     * Exit with appropriate code (0 for success, 1 for errors)

2. Create tests/test_joke_pipeline.py:
   - Test full pipeline with sample email → ready_for_review
   - Test priority pipeline processed before main
   - Test rejection at various stages
   - Test multiple files
   - Test command-line argument parsing
   - Test --stage flag for single stage execution
   - Use real temporary directories with full pipeline structure
   - Verify end-to-end file progression

3. Create tests/fixtures/full_pipeline/:
   - Complete test setup with:
     * Sample emails
     * Mock external scripts
     * Expected outputs at each stage
   - Test data for success path
   - Test data for various rejection scenarios

Implementation notes:
- Use argparse for command-line arguments
- Comprehensive logging
- Error handling for missing dependencies
- Clear progress indicators
- Exit codes: 0 = success, 1 = error
- Support running individual stages for debugging

Testing approach:
- End-to-end integration testing
- Test complete success path
- Test each rejection path
- Verify file movement through all stages
- Test with multiple files
- Use real filesystem and external scripts (mocked)

Deliverables:
- joke-pipeline.py
- tests/test_joke_pipeline.py
- tests/fixtures/full_pipeline/ setup
- All tests passing
- Executable script with clear help text
```

---

## Step 16: Integration Testing & Documentation

```
Create comprehensive integration tests and documentation for the complete system.

Build on: All previous steps (complete implementation)

Requirements:
1. Create tests/test_integration.py with:

   Integration test suite:
   - Test complete pipeline with 10+ diverse jokes
   - Test scenarios:
     * Clean jokes that pass all stages
     * Duplicate jokes (rejected at parsed stage)
     * Unclean jokes (rejected at cleanliness stage)
     * Poorly formatted jokes (rejected at format stage)
     * Uncategorizable jokes (rejected at category stage)
     * Jokes missing titles (titles generated successfully)
     * Jokes with existing titles (titles preserved)
   - Test priority vs main pipeline processing order
   - Test retry logic with transient failures
   - Test concurrent execution (multiple pipeline runs)
   - Verify all metadata fields populated correctly
   - Verify file counts in all directories
   - Test with real Ollama, real external scripts (or mocks if unavailable)

2. Create comprehensive test data:
   - tests/fixtures/integration/:
     * 10+ sample emails with various joke types
     * Expected outputs for each stage
     * Sample TF-IDF corpus for duplicate testing
   - Document expected flow for each test joke

3. Create README.md with:
   - Project overview
   - Requirements (Python version, Ollama, external scripts)
   - Installation instructions
   - Configuration guide (config.py setup)
   - Directory structure explanation
   - Running the pipeline (command-line examples)
   - Testing instructions
   - Troubleshooting guide
   - Common issues and solutions

4. Create TESTING.md with:
   - Test suite overview
   - Running tests (pytest commands)
   - Test coverage requirements
   - Adding new tests
   - Mock vs real dependencies
   - Test data management

5. Create setup.py or requirements.txt:
   - List all Python dependencies
   - Specify versions
   - Include development dependencies (pytest, etc.)

6. Performance and validation:
   - Run complete pipeline with 20+ jokes
   - Measure processing time for each stage
   - Verify no file corruption
   - Verify atomic operations
   - Verify logging completeness
   - Check for resource leaks

Implementation notes:
- Comprehensive documentation
- Clear setup instructions
- Example configurations
- Troubleshooting tips
- Production readiness checklist

Testing approach:
- Large-scale integration testing
- Diverse test cases
- Real-world scenarios
- Performance measurement
- Error recovery testing

Deliverables:
- tests/test_integration.py
- tests/fixtures/integration/ with comprehensive test data
- README.md
- TESTING.md
- requirements.txt
- All tests passing (unit + integration)
- Complete, production-ready system

Success criteria:
- Can process 20+ jokes end-to-end
- All rejection scenarios work correctly
- Documentation complete and accurate
- Setup instructions verified
- Ready for deployment and cron scheduling
```

---

## Testing Philosophy

Throughout all steps, follow these testing principles:

1. **Real Data**: Use actual files, real filesystem operations, real API calls when possible
2. **No Mocking Core Logic**: Mock only external dependencies (Ollama, external scripts) when unavailable
3. **Integration Focus**: Test how components work together, not just in isolation
4. **Edge Cases**: Test boundary conditions, error scenarios, and unexpected inputs
5. **Incremental**: Each step builds on verified previous steps
6. **Comprehensive**: Aim for 80%+ code coverage
7. **Clear Failures**: Tests should clearly indicate what went wrong
8. **Repeatable**: Tests should pass consistently in any environment

## Prompt Usage Notes

- Execute prompts in order (Step 1 → Step 16)
- Complete all tests before moving to next step
- Verify all previous tests still pass before proceeding
- Each step should leave the codebase in a working state
- Integration points are explicitly called out
- No orphaned code - everything wired together by Step 15

## Additional Context for LLM

When implementing these prompts:
- Follow PEP 8 style guidelines
- Include comprehensive docstrings
- Add type hints where helpful
- Use descriptive variable names
- Handle errors gracefully with clear messages
- Log extensively for debugging
- Think about edge cases
- Prioritize correctness over performance initially
- Test thoroughly before moving on
