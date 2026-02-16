# Step 11: Stage 03 - Deduped (Cleanliness Check)

Implement cleanliness check stage using Ollama LLM.

Build on: Steps 5, 10 (StageProcessor, OllamaClient)

Requirements:
1. Create stage_deduped.py with:

   DedupedProcessor(StageProcessor):
   - Constructor:
     * Sets stage_name="deduped", output_stage="clean_checked", reject_stage="rejected_cleanliness"
     * Initializes OllamaClient with config.ollama_config
   
   - Implement process_file(filepath, headers, content):
     * Construct system prompt: "You are a content moderator evaluating jokes for appropriateness."
     * Construct user prompt:
       """
       Evaluate this joke for cleanliness and appropriateness:
       
       {content}
       
       Determine if this joke is:
       - Clean (no profanity, sexual content, or offensive material)
       - Appropriate for general audiences
       
       Respond with:
       Status: PASS or FAIL
       Confidence: <0-100 integer>
       Reason: <brief explanation>
       """
     * Call ollama_client.generate(system_prompt, user_prompt)
     * Parse response for Status, Confidence, Reason
     * Add Cleanliness-Status to headers (PASS or FAIL)
     * Add Cleanliness-Confidence to headers (integer 0-100)
     * If Status is FAIL:
       - Return (False, headers, content, f"Cleanliness check failed: {reason}")
     * If Confidence < config.CLEANLINESS_MIN_CONFIDENCE:
       - Return (False, headers, content, f"Confidence {confidence} below minimum {min}")
     * If Status is PASS and Confidence >= minimum:
       - Return (True, headers, content, "")
     * Handle LLM errors (return failure)

2. Create tests/test_stage_deduped.py:
   - Test with clean joke (should pass)
   - Test with questionable joke (may fail)
   - Test with high confidence (should pass)
   - Test with low confidence (should fail even if status is PASS)
   - Test metadata updates (Cleanliness-Status, Cleanliness-Confidence)
   - Test LLM error handling
   - Test with real Ollama if available
   - Verify files moved to correct directories

3. Create tests/fixtures/jokes/:
   - clean_joke.txt (definitely clean)
   - questionable_joke.txt (borderline)

Implementation notes:
- Clear, specific prompts to LLM
- Parse responses robustly (handle variations)
- Enforce confidence threshold strictly
- Log LLM responses for debugging
- Handle LLM failures gracefully

Testing approach:
- Test with real Ollama if available
- Use mock responses if Ollama not available
- Verify metadata in output files
- Test threshold enforcement
- Test various joke content

Deliverables:
- stage_deduped.py
- tests/test_stage_deduped.py
- tests/fixtures/jokes/ with sample jokes
- All tests passing