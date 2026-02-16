# Step 2: File Metadata Parser & Writer

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