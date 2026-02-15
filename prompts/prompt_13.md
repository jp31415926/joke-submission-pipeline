# Step 13: Stage 05 - Formatted (Categorization)

Implement categorization stage to assign 1-3 categories to jokes.

Build on: Steps 5, 10 (StageProcessor, OllamaClient)

Requirements:
1. Create stage_formatted.py with:

   FormattedProcessor(StageProcessor):
   - Constructor:
     * Sets stage_name="formatted", output_stage="categorized", reject_stage="rejected_category"
     * Initializes OllamaClient
   
   - Implement process_file(filepath, headers, content):
     * Construct system prompt: "You are a joke categorization expert."
     * Construct user prompt:
       """
       Categorize this joke into 1-3 categories from this list:
       {', '.join(config.VALID_CATEGORIES)}
       
       Joke:
       {content}
       
       Respond with:
       Categories: <comma-separated list of 1-3 categories>
       Confidence: <0-100 integer>
       Reasoning: <brief explanation>
       """
     * Call ollama_client.generate(system_prompt, user_prompt)
     * Parse response for Categories, Confidence, Reasoning
     * Validate categories against config.VALID_CATEGORIES
     * Verify 1-3 categories (not more, not less)
     * Add Categories to headers (comma-separated string)
     * Add Category-Confidence to headers (integer)
     * If invalid categories or count wrong:
       - Return (False, headers, content, f"Invalid categories: {reason}")
     * If Confidence < config.CATEGORIZATION_MIN_CONFIDENCE:
       - Return (False, headers, content, f"Confidence {confidence} too low")
     * Return (True, headers, content, "")

2. Create tests/test_stage_formatted.py:
   - Test with joke matching 1 category
   - Test with joke matching 2 categories
   - Test with joke matching 3 categories
   - Test with invalid category (should fail)
   - Test with too many categories (should fail)
   - Test with too few categories (should fail)
   - Test confidence threshold
   - Test metadata updates
   - Test with real Ollama if available
   - Verify category validation

3. Add to tests/fixtures/jokes/:
   - pun_joke.txt (Puns category)
   - dad_joke.txt (Dad Jokes category)
   - animal_pun.txt (Animals + Puns categories)

Implementation notes:
- Strict category validation
- Enforce 1-3 category limit from config
- Case-insensitive category matching
- Log categorization results
- Handle LLM not following format

Testing approach:
- Test with various joke types
- Verify category validation
- Test edge cases (exactly 1, exactly 3)
- Ensure only valid categories accepted

Deliverables:
- stage_formatted.py
- tests/test_stage_formatted.py
- Updated tests/fixtures/jokes/
- All tests passing