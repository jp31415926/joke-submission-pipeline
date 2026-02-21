# Step 8: Stage 01 - Incoming (Email Extraction)

Implement the first pipeline stage that processes emails through joke-extract.py.

Build on: Steps 5, 6, 7 (StageProcessor, UUID generation, external scripts)

Requirements:
1. Create stage_incoming.py with:

   IncomingProcessor(StageProcessor):
   - Constructor sets stage_name="incoming", output_stage="parsed", reject_stage="rejected_parse"
   
   - Implement process_file(filepath, headers, content):
     * Extract email filename from filepath
     * Create temporary success and fail directories
     * Call joke-extract.py: run_external_script(config.JOKE_EXTRACTOR, [success_dir, fail_dir, filepath])
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