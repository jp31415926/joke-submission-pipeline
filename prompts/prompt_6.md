# Step 6: UUID Generation & Metadata Initialization

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