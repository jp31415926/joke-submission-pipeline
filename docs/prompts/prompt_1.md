# Step 1: Project Structure & Configuration

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