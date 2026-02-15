# Step 14: Stage 06/07 - Categorized/Titled (Title Generation & Final Validation)

Implement title generation for jokes with blank titles and final validation before ready-for-review.

Build on: Steps 5, 10 (StageProcessor, OllamaClient)

Requirements:
1. Create stage_categorized.py with:

   CategorizedProcessor(StageProcessor):
   - Constructor:
     * Sets stage_name="categorized", output_stage="ready_for_review", reject_stage="rejected_titled"
     * Initializes OllamaClient
   
   - Implement process_file(filepath, headers, content):
     * Check if Title field exists and is not blank
     * If Title is blank or missing:
       - Construct system prompt: "You are a creative title writer for jokes."
       - Construct user prompt:
         """
         Create a short, catchy title for this joke:
         
         {content}
         
         Categories: {headers.get('Categories', 'Unknown')}
         
         Respond with:
         Title: <a short, engaging title>
         Confidence: <0-100 integer>
         """
       - Call ollama_client.generate(system_prompt, user_prompt)
       - Parse response for Title, Confidence
       - Update Title in headers
       - If Confidence < 70:
         * Return (False, headers, content, "Title generation confidence too low")
     * Perform final validation:
       - Required fields: Joke-ID, Title, Submitter, Source-Email-File, Pipeline-Stage, Categories
       - Required fields must not be blank
       - Cleanliness-Status must be PASS
       - Format-Status must be PASS
       - Content must be > 10 characters
     * If validation fails:
       - Return (False, headers, content, f"Validation failed: {specific_failures}")
     * If all validations pass:
       - Return (True, headers, content, "")

2. Create tests/test_stage_categorized.py:
   - Test with blank title (should generate)
   - Test with existing title (should preserve)
   - Test title generation
   - Test final validation with all fields present
   - Test final validation with missing Joke-ID (should fail)
   - Test final validation with blank Title (should fail)
   - Test final validation with short content (should fail)
   - Test final validation with Cleanliness-Status FAIL (should fail)
   - Test with real Ollama if available
   - Verify complete jokes reach ready_for_review/

3. Create comprehensive test fixture:
   - tests/fixtures/jokes/complete_joke.txt (all fields, should pass)
   - tests/fixtures/jokes/blank_title_joke.txt (needs title generation)
   - tests/fixtures/jokes/incomplete_joke.txt (missing required fields)

Implementation notes:
- Only generate title if blank
- Preserve existing titles
- Comprehensive validation before ready-for-review
- Specific error messages for each validation failure
- Log validation results

Testing approach:
- Test title generation separately
- Test validation separately
- Test complete flow
- Verify all required fields
- Test various failure scenarios

Deliverables:
- stage_categorized.py
- tests/test_stage_categorized.py
- tests/fixtures/jokes/ with validation test cases
- All tests passing