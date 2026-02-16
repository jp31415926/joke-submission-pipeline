# Step 9: Stage 02 - Parsed (Duplicate Detection)

Implement duplicate detection stage using search_tfidf.py.

Build on: Steps 5, 7 (StageProcessor, external scripts)

Requirements:
1. Create stage_parsed.py with:

   ParsedProcessor(StageProcessor):
   - Constructor sets stage_name="parsed", output_stage="deduped", reject_stage="rejected_duplicate"
   
   - Implement process_file(filepath, headers, content):
     * Write content to temporary file for search_tfidf.py
     * Call search_tfidf.py: run_external_script(config.SEARCH_TFIDF, [temp_file])
     * Parse score using parse_tfidf_score(stdout)
     * Add Duplicate-Score to headers (integer)
     * Add Duplicate-Threshold to headers (from config)
     * Compare score to config.DUPLICATE_THRESHOLD
     * If score >= threshold:
       - Return (False, headers, content, f"Duplicate score {score} >= threshold {threshold}")
     * If score < threshold:
       - Return (True, headers, content, "")
     * Handle search_tfidf.py errors (return code != 0)
     * Clean up temporary file

2. Create tests/test_stage_parsed.py:
   - Create mock search_tfidf.py that returns configurable scores
   - Test with score below threshold (should pass)
   - Test with score at threshold (should fail)
   - Test with score above threshold (should fail)
   - Test metadata updates (Duplicate-Score, Duplicate-Threshold)
   - Test search_tfidf.py failure handling
   - Test with real files in temp directories
   - Verify files moved to deduped/ or rejected_duplicate/

3. Update tests/fixtures/mock_search_tfidf.py:
   - Accept environment variable MOCK_SCORE to return specific scores
   - Default to score 30 (below threshold)

Implementation notes:
- Create temporary file for search_tfidf.py input
- Parse only the first integer from output
- Use >= for threshold comparison (duplicate if score meets or exceeds threshold)
- Log duplicate score for every file
- Clean up temporary files

Testing approach:
- Use mock search_tfidf.py with controlled output
- Test threshold edge cases (exactly at threshold)
- Verify metadata in output files
- Test error handling

Deliverables:
- stage_parsed.py
- tests/test_stage_parsed.py
- Updated tests/fixtures/mock_search_tfidf.py
- All tests passing