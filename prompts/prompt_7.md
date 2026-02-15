# Step 7: External Script Integration Utilities

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