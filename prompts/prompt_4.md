# Step 4: Logging Infrastructure

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