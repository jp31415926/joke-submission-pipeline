# Step 12: Stage 04 - Clean Checked (Formatting)

Implement formatting stage to improve joke grammar and punctuation.

Build on: Steps 5, 10 (StageProcessor, OllamaClient)

Requirements:
1. Create stage_clean_checked.py with:

   CleanCheckedProcessor(StageProcessor):
   - Constructor:
     * Sets stage_name="clean_checked", output_stage="formatted", reject_stage="rejected_format"
     * Initializes OllamaClient
   
   - Implement process_file(filepath, headers, content):
     * Construct system prompt: "You are an editor improving joke formatting and grammar."
     * Construct user prompt:
       """
       Improve the grammar, punctuation, and formatting of this joke while preserving its meaning and humor:
       
       {content}
       
       Respond with:
       Formatted-Joke: <the improved joke text>
       Confidence: <0-100 integer indicating quality of original>
       Changes: <brief description of changes made>
       """
     * Call ollama_client.generate(system_prompt, user_prompt)
     * Parse response for Formatted-Joke, Confidence, Changes
     * Add Format-Status: PASS to headers
     * Add Format-Confidence to headers (integer)
     * If Confidence < config.CATEGORIZATION_MIN_CONFIDENCE:
       - Return (False, headers, content, f"Format confidence {confidence} too low")
     * Update content with formatted joke text
     * Return (True, headers, formatted_content, "")
     * Handle LLM errors

2. Create tests/test_stage_clean_checked.py:
   - Test with well-formatted joke (minimal changes)
   - Test with poorly formatted joke (significant improvements)
   - Test confidence threshold enforcement
   - Test content update (formatted version replaces original)
   - Test metadata updates
   - Test with real Ollama if available
   - Verify formatted content in output files

3. Add to tests/fixtures/jokes/:
   - poorly_formatted_joke.txt (needs improvement)
   - well_formatted_joke.txt (already good)

Implementation notes:
- Preserve joke content and humor
- Update content in file, not just metadata
- Log changes made by LLM
- Handle cases where LLM doesn't follow format
- Confidence reflects quality of ORIGINAL, not formatted version

Testing approach:
- Compare original and formatted content
- Verify content actually updated
- Test with various formatting issues
- Verify metadata updates

Deliverables:
- stage_clean_checked.py
- tests/test_stage_clean_checked.py
- Updated tests/fixtures/jokes/
- All tests passing