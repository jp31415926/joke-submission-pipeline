# Step 10: Ollama LLM Integration Utility

Create a reusable client for interacting with Ollama API.

Build on: Step 1 (config.py with ollama_config), Step 4 (logging)

Requirements:
1. Create ollama_client.py with:

   OllamaClient:
   - Constructor accepts ollama_config dictionary from config
   - Store API URL, model name, and options
   
   - Method generate(system_prompt, user_prompt):
     * Build request body with:
       - model: from config
       - prompt: user_prompt
       - system: system_prompt
       - stream: False (we want complete responses)
       - options: from config
     * POST to ollama_api_url
     * Parse JSON response
     * Extract response text from response['response']
     * Return response text
     * Handle network errors, timeout, invalid JSON
     * Log request and response (truncated for readability)
   
   - Method parse_structured_response(response_text, expected_keys):
     * Attempt to parse response as JSON
     * If not JSON, look for key-value pairs in format "Key: Value"
     * Return dictionary with extracted values
     * Handle missing keys gracefully
   
   - Method extract_confidence(response_dict):
     * Look for confidence score in response
     * Try keys: "confidence", "Confidence", "score"
     * Parse as integer (0-100)
     * Return integer or None if not found
     * Handle non-integer values

2. Create tests/test_ollama_client.py:
   - Test generate() with mock Ollama server (use requests_mock or similar)
   - Test successful response parsing
   - Test network error handling
   - Test timeout handling
   - Test parse_structured_response with JSON response
   - Test parse_structured_response with key-value format
   - Test extract_confidence with various formats
   - If real Ollama available, test with actual API call

3. Optional: Create tests/mock_ollama_server.py:
   - Simple Flask server that mimics Ollama API
   - Returns canned responses for testing
   - Use only if real Ollama not available for tests

Implementation notes:
- Use requests library for HTTP calls
- Set reasonable timeout (30 seconds)
- Handle rate limiting (429 responses)
- Parse both JSON and text responses
- Log all API calls for debugging

Testing approach:
- Prefer testing with real Ollama if available
- Use mock server for CI/CD environments
- Test error conditions thoroughly
- Verify confidence score parsing with various inputs

Deliverables:
- ollama_client.py
- tests/test_ollama_client.py
- (Optional) tests/mock_ollama_server.py
- All tests passing