# Step 3: Atomic File Operations

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