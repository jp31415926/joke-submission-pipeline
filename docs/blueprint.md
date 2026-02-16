# Joke Submission Pipeline - Development Blueprint

## Project Overview

A file-based state machine that processes joke submissions from emails through multiple LLM-enhanced stages, from extraction to ready-for-review status.

## Architecture Principles

- **File-based state machine**: Each stage reads from input directory, processes, writes to output
- **Atomic operations**: All file moves use tmp/ subdirectories
- **Config-driven**: All paths, thresholds, and settings in config.py
- **Dual pipelines**: Priority and main pipelines, priority processed first
- **Retry logic**: 2 retries (3 total attempts) on processing errors
- **Real integration**: Uses actual external scripts (joke-extract.py, search_tfidf.py) and Ollama LLM

## Technology Stack

- Python 3.x
- Ollama (llama3 model) for LLM operations
- External scripts: joke-extract.py, build_tfidf.py, search_tfidf.py
- Cron for orchestration
- File-based storage with plain text headers

---

## Development Phases

### Phase 1: Foundation & Utilities (Steps 1-4)
Build the core infrastructure for file operations, configuration, and metadata handling.

### Phase 2: Stage Processing Framework (Steps 5-7)
Create the reusable framework for stage processing with retry logic and atomic operations.

### Phase 3: Stage Implementations (Steps 8-14)
Implement each pipeline stage one at a time, building on previous work.

### Phase 4: Integration & Orchestration (Steps 15-16)
Wire everything together and create the main orchestration script.

---

## Detailed Implementation Steps

### **Step 1: Project Structure & Configuration**
**Goal**: Set up directory structure and configuration management

**Deliverables**:
- Create project directory structure
- Implement config.py with all required settings
- Create directory initialization script
- Basic test to verify config loading

**Components**:
- `config.py`: All configuration constants and paths
- `setup_directories.py`: Creates pipeline directories with tmp/ subdirectories
- `test_config.py`: Verifies configuration loads correctly

**Testing**:
- Verify config.py loads without errors
- Verify all expected constants are present
- Test directory creation script creates correct structure
- Verify both main and priority pipelines are created

**Success Criteria**:
- All directories created correctly with tmp/ subdirectories
- Config loads and provides all required values
- Tests pass

---

### **Step 2: File Metadata Parser & Writer**
**Goal**: Create utilities to read/write joke file headers

**Deliverables**:
- Parse joke file headers into dictionary
- Write headers and content to file
- Handle missing/optional fields
- Comprehensive tests with real file formats

**Components**:
- `file_utils.py`:
  - `parse_joke_file(filepath)`: Returns (headers_dict, content_string)
  - `write_joke_file(filepath, headers_dict, content)`: Writes file with headers
  - `validate_headers(headers_dict, required_fields)`: Validates required fields present

**Testing**:
- Test parsing sample files from joke-extract.py format
- Test parsing files with full headers
- Test writing files and reading them back
- Test missing optional fields
- Test validation with missing required fields
- Use real sample joke files

**Success Criteria**:
- Can parse joke-extract.py output format
- Can parse full pipeline format
- Round-trip testing (write then read) produces identical data
- Validation correctly identifies missing required fields

---

### **Step 3: Atomic File Operations**
**Goal**: Implement safe file movement using tmp/ subdirectories

**Deliverables**:
- Atomic file move operations
- Safe file writing to tmp/ then move
- Cleanup on failure
- Tests with real filesystem operations

**Components**:
- `file_utils.py` additions:
  - `atomic_write(target_path, headers_dict, content)`: Write to tmp/, then move
  - `atomic_move(source_path, dest_dir)`: Move file to dest_dir via tmp/
  - `safe_cleanup(filepath)`: Remove file if exists

**Testing**:
- Test atomic write creates file in tmp/ first
- Test atomic move uses tmp/ subdirectory
- Test partial failure cleanup
- Test concurrent operations don't collide
- Use real files and directories

**Success Criteria**:
- Files never appear incomplete in destination
- Failed operations leave no partial files
- Concurrent operations handled safely

---

### **Step 4: Logging Infrastructure**
**Goal**: Implement consistent logging with Joke-ID prefix

**Deliverables**:
- Centralized logging setup
- Joke-ID prefixed messages
- Log file management
- Tests verifying log output

**Components**:
- `logging_utils.py`:
  - `setup_logging(log_dir, log_level)`: Configure logging
  - `get_logger(name)`: Get logger instance
  - `log_with_joke_id(logger, level, joke_id, message)`: Log with prefix

**Testing**:
- Test logger creation and configuration
- Test Joke-ID prefixed messages appear correctly
- Test different log levels
- Verify log files created in correct location

**Success Criteria**:
- All log messages include Joke-ID when available
- Logs written to configured directory
- Log levels work correctly

---

### **Step 5: Stage Processor Base Class**
**Goal**: Create reusable base class for all stage processors

**Deliverables**:
- Abstract base class with common functionality
- Priority pipeline handling (check priority first)
- Retry logic (2 retries = 3 total attempts)
- Move to reject directory on failure
- Tests with mock stage implementation

**Components**:
- `stage_processor.py`:
  - `StageProcessor` (abstract base class):
    - `process_file(filepath)`: Abstract method to implement
    - `run()`: Main execution loop
    - `_process_with_retry(filepath)`: Retry logic wrapper
    - `_move_to_output(filepath, headers, content)`: Success path
    - `_move_to_reject(filepath, headers, content, reason)`: Failure path
    - Priority pipeline checking logic

**Testing**:
- Create mock stage processor
- Test priority pipeline processed before main
- Test retry logic (fail twice, succeed third time)
- Test rejection after max retries
- Test metadata updates during stage transitions
- Use real files

**Success Criteria**:
- Priority files processed first
- Retry logic works correctly (3 total attempts)
- Files moved to correct directories
- Metadata updated properly
- Rejection reasons recorded

---

### **Step 6: UUID Generation & Metadata Initialization**
**Goal**: Create utilities for generating UUIDs and initializing file metadata

**Deliverables**:
- UUID generation for Joke-ID
- Metadata initialization for new files
- Source email file tracking
- Tests with real UUID generation

**Components**:
- `file_utils.py` additions:
  - `generate_joke_id()`: Generate UUID for Joke-ID
  - `initialize_metadata(headers, email_filename)`: Add Joke-ID, Source-Email-File, Pipeline-Stage

**Testing**:
- Test UUID generation creates valid UUIDs
- Test metadata initialization adds required fields
- Test existing metadata is preserved
- Verify UUID uniqueness across multiple calls

**Success Criteria**:
- Valid UUIDs generated
- Metadata properly initialized
- No data loss during initialization

---

### **Step 7: External Script Integration Utilities**
**Goal**: Create utilities for calling external scripts safely

**Deliverables**:
- Subprocess wrapper with error handling
- Script output parsing
- Return code checking
- Tests with actual external script calls

**Components**:
- `external_scripts.py`:
  - `run_external_script(script_path, args, timeout=None)`: Run script, return (return_code, stdout, stderr)
  - `parse_tfidf_score(output)`: Parse search_tfidf.py output to extract score

**Testing**:
- Test successful script execution
- Test script failure handling
- Test timeout handling
- Test output parsing (search_tfidf.py format)
- Use real external scripts if available, otherwise mock

**Success Criteria**:
- Scripts execute correctly
- Errors captured and logged
- Output parsed correctly
- Timeouts handled

---

### **Step 8: Stage 01 - Incoming (Email Extraction)**
**Goal**: Process emails through joke-extract.py and prepare for pipeline

**Deliverables**:
- Call joke-extract.py for email files
- Generate UUID for each extracted joke
- Add initial metadata (Joke-ID, Source-Email-File, Pipeline-Stage)
- Move to parsed/ or rejected_parse/
- Tests with real email files

**Components**:
- `stage_incoming.py`:
  - `IncomingProcessor(StageProcessor)`: Implements process_file()
  - Calls joke-extract.py
  - Processes extracted jokes
  - Adds metadata

**Testing**:
- Test with sample Maildir email files
- Test email with single joke
- Test email with multiple jokes
- Test email with no jokes
- Test joke-extract.py failure handling
- Verify UUID generation and metadata
- Verify files moved to correct directories

**Success Criteria**:
- Emails processed through joke-extract.py
- Each joke gets unique UUID
- Metadata properly initialized
- Files in correct output directory
- Failures moved to reject directory

---

### **Step 9: Stage 02 - Parsed (Duplicate Detection)**
**Goal**: Check for duplicate jokes using TF-IDF search

**Deliverables**:
- Call search_tfidf.py for each joke
- Parse duplicate score
- Compare against threshold
- Add Duplicate-Score and Duplicate-Threshold to metadata
- Move to deduped/ or rejected_duplicate/
- Tests with real TF-IDF calls

**Components**:
- `stage_parsed.py`:
  - `ParsedProcessor(StageProcessor)`: Implements process_file()
  - Calls search_tfidf.py
  - Parses score from output
  - Updates metadata

**Testing**:
- Test with jokes that should pass (low score)
- Test with jokes that should fail (high score)
- Test search_tfidf.py error handling
- Verify score parsing
- Verify threshold comparison
- Use real search_tfidf.py if available

**Success Criteria**:
- Duplicate scores calculated correctly
- Threshold comparison works
- Metadata updated with scores
- Files moved to correct directories
- Rejections have proper reason

---

### **Step 10: Ollama LLM Integration Utility**
**Goal**: Create reusable utility for Ollama API calls

**Deliverables**:
- Ollama API client
- Prompt construction
- Response parsing
- Confidence score extraction
- Error handling
- Tests with real Ollama calls

**Components**:
- `ollama_client.py`:
  - `OllamaClient`: 
    - `__init__(config)`: Initialize with Ollama config
    - `generate(system_prompt, user_prompt)`: Call Ollama API
    - `parse_response(response_text)`: Parse structured responses
    - `extract_confidence(response)`: Extract confidence score (0-100)

**Testing**:
- Test Ollama API connectivity
- Test prompt generation
- Test response parsing
- Test confidence extraction
- Test error handling (API down, timeout, etc.)
- Use real Ollama instance

**Success Criteria**:
- Can communicate with Ollama API
- Responses parsed correctly
- Confidence scores extracted (0-100 integers)
- Errors handled gracefully

---

### **Step 11: Stage 03 - Deduped (Cleanliness Check)**
**Goal**: Use LLM to check joke cleanliness and appropriateness

**Deliverables**:
- Construct cleanliness check prompt
- Call Ollama LLM
- Parse PASS/FAIL status and confidence
- Reject if confidence < threshold or status = FAIL
- Update metadata
- Tests with real jokes and Ollama

**Components**:
- `stage_deduped.py`:
  - `DedupedProcessor(StageProcessor)`: Implements process_file()
  - Cleanliness prompt construction
  - LLM response parsing
  - Metadata updates

**Testing**:
- Test with clean jokes (should pass)
- Test with questionable jokes (may fail)
- Test confidence threshold enforcement
- Test LLM error handling
- Verify metadata updates
- Use real Ollama and real jokes

**Success Criteria**:
- Cleanliness checks run successfully
- PASS/FAIL status determined correctly
- Confidence scores extracted and compared
- Metadata updated properly
- Rejections include reason

---

### **Step 12: Stage 04 - Clean Checked (Formatting)**
**Goal**: Use LLM to improve joke formatting and grammar

**Deliverables**:
- Construct formatting prompt
- Call Ollama LLM
- Extract formatted joke text
- Update joke content in file
- Update metadata (Format-Status, Format-Confidence)
- Tests with real jokes

**Components**:
- `stage_clean_checked.py`:
  - `CleanCheckedProcessor(StageProcessor)`: Implements process_file()
  - Formatting prompt construction
  - Extract formatted text from LLM response
  - Update joke content

**Testing**:
- Test with jokes needing formatting
- Test with well-formatted jokes
- Test confidence threshold
- Verify joke content updated
- Verify metadata updated
- Use real Ollama

**Success Criteria**:
- Jokes formatted correctly
- Content updated in files
- Metadata includes status and confidence
- Poor formatting rejected if confidence too low

---

### **Step 13: Stage 05 - Formatted (Categorization)**
**Goal**: Use LLM to assign 1-3 categories to jokes

**Deliverables**:
- Construct categorization prompt with valid categories
- Call Ollama LLM
- Parse category list (1-3 categories)
- Validate categories against VALID_CATEGORIES
- Update metadata
- Tests with diverse jokes

**Components**:
- `stage_formatted.py`:
  - `FormattedProcessor(StageProcessor)`: Implements process_file()
  - Categorization prompt with valid category list
  - Parse and validate categories
  - Metadata updates

**Testing**:
- Test with jokes matching different categories
- Test 1, 2, and 3 category assignments
- Test invalid category rejection
- Test confidence threshold
- Verify metadata updates
- Use real Ollama

**Success Criteria**:
- Categories assigned correctly (1-3)
- All categories from VALID_CATEGORIES list
- Confidence threshold enforced
- Metadata updated properly

---

### **Step 14: Stage 06/07 - Categorized/Titled (Title Generation & Validation)**
**Goal**: Generate titles for jokes that lack them, then validate all fields

**Deliverables**:
- Check if Title field is blank
- If blank, use LLM to generate title
- If not blank, skip title generation
- Validate all required fields
- Move to ready_for_review/ or reject
- Tests with titled and untitled jokes

**Components**:
- `stage_categorized.py`:
  - `CategorizedProcessor(StageProcessor)`: Implements process_file()
  - Check for blank title
  - Title generation prompt
  - Final validation logic
  - Comprehensive field checking

**Testing**:
- Test with blank title (should generate)
- Test with existing title (should skip)
- Test validation with all fields present
- Test validation with missing fields
- Test minimum content length
- Use real Ollama

**Success Criteria**:
- Blank titles get generated
- Existing titles preserved
- All required fields validated
- Content length checked
- Complete jokes reach ready_for_review/
- Incomplete jokes rejected with reason

---

### **Step 15: Main Orchestration Script**
**Goal**: Create main script that runs all stages in sequence

**Deliverables**:
- Main pipeline runner
- Process priority pipeline first, then main
- Run all stages in order
- Command-line interface
- Logging of overall execution
- Tests with end-to-end scenarios

**Components**:
- `joke-pipeline.py`:
  - Main entry point
  - Instantiate all stage processors
  - Run stages in sequence
  - Handle errors gracefully
  - Command-line arguments (--stage, --pipeline, etc.)

**Testing**:
- Test full pipeline with sample email
- Test priority vs main pipeline ordering
- Test with multiple files
- Test failure handling at different stages
- Test end-to-end with real data
- Verify files progress through all stages

**Success Criteria**:
- Single script runs entire pipeline
- Priority processed before main
- All stages execute in order
- End-to-end processing works
- Logging shows complete workflow

---

### **Step 16: Integration Testing & Documentation**
**Goal**: Comprehensive testing and final documentation

**Deliverables**:
- End-to-end integration tests
- Test data preparation
- Performance verification
- README documentation
- Usage examples

**Components**:
- `test_integration.py`:
  - Full pipeline tests with real data
  - Multiple joke scenarios
  - Error recovery testing
  - Validation testing
- `README.md`:
  - Setup instructions
  - Configuration guide
  - Running the pipeline
  - Troubleshooting

**Testing**:
- Run full pipeline with 10+ sample jokes
- Test various failure scenarios
- Verify reject directories
- Test retry logic end-to-end
- Performance measurement

**Success Criteria**:
- Complete pipeline processes jokes correctly
- All rejection scenarios work
- Documentation complete and accurate
- System ready for production use

---

## Step Dependencies

```
Step 1 (Config) → Step 2 (File Utils) → Step 3 (Atomic Ops) → Step 4 (Logging)
                                              ↓
                                         Step 5 (Base Processor)
                                              ↓
                                         Step 6 (UUID) + Step 7 (External Scripts)
                                              ↓
                                         Step 8 (Stage 01: Incoming)
                                              ↓
                                         Step 9 (Stage 02: Parsed)
                                              ↓
                                         Step 10 (Ollama Client)
                                              ↓
                                         Step 11 (Stage 03: Deduped)
                                              ↓
                                         Step 12 (Stage 04: Clean Checked)
                                              ↓
                                         Step 13 (Stage 05: Formatted)
                                              ↓
                                         Step 14 (Stage 06/07: Categorized/Titled)
                                              ↓
                                         Step 15 (Main Orchestration)
                                              ↓
                                         Step 16 (Integration Testing)
```

---

## Testing Strategy

### Test Data Requirements
- Sample Maildir email files (3-5 different formats)
- Sample joke files from joke-extract.py
- Jokes with various categories
- Jokes with and without titles
- Jokes that should be clean and unclean
- Duplicate jokes for testing TF-IDF

### Testing Approach
- **Unit tests**: Each module tested independently
- **Integration tests**: Stage-to-stage transitions
- **End-to-end tests**: Full pipeline with real data
- **Real dependencies**: Use actual Ollama, actual external scripts
- **No mocks for data**: Real files, real API calls
- **Regression tests**: Ensure changes don't break existing functionality

### Test Coverage Goals
- 80%+ code coverage
- All critical paths tested
- All error conditions tested
- All rejection scenarios tested

---

## Key Design Decisions

1. **File-based state machine**: Simple, debuggable, no database needed
2. **Atomic operations**: Prevents partial/corrupt files
3. **Config-driven**: Easy to modify without code changes
4. **Priority pipeline**: Separate from main, processed first
5. **Retry logic**: 2 retries = 3 total attempts before rejection
6. **Metadata in files**: All state visible in file headers
7. **One file at a time**: Simple batch processing, easy to reason about
8. **Inheritance**: StageProcessor base class for code reuse
9. **External scripts**: Integration with existing tools
10. **Real LLM**: Actual Ollama calls, not mocked

---

## Risk Mitigation

1. **Ollama API failures**: Retry logic, clear error messages
2. **External script failures**: Subprocess error handling, logging
3. **File corruption**: Atomic operations, tmp/ subdirectories
4. **Duplicate UUIDs**: Use Python's uuid library (extremely unlikely collision)
5. **Invalid LLM responses**: Robust parsing, validation, rejection on parse failure
6. **Missing dependencies**: Clear error messages, setup documentation
7. **Configuration errors**: Validation on startup

---

## Success Metrics

- ✅ All stages process files correctly
- ✅ Atomic operations prevent file corruption
- ✅ Priority pipeline processed before main
- ✅ Retry logic handles transient failures
- ✅ LLM integration works reliably
- ✅ External scripts integrated correctly
- ✅ Comprehensive test coverage
- ✅ Clear, actionable logs
- ✅ Easy to configure and deploy
- ✅ Ready for cron-based orchestration

---

## Next Steps After Completion

1. Deploy to production environment
2. Set up cron jobs for each stage
3. Configure log rotation
4. Set up monitoring and alerting
5. Create operational runbooks
6. Train users on manual review process
7. Implement build_tfidf.py integration for corpus updates
