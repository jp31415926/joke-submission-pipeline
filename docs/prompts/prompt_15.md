# Step 15: Main Orchestration Script

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