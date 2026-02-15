# Step 5: Stage Processor Base Class

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