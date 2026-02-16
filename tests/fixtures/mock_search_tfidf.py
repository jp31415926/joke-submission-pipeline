#!/usr/bin/env python3
"""Mock search_tfidf.py for testing."""
import os
import sys

# Get mock score from environment variable, default to 30
mock_score = int(os.environ.get('MOCK_SCORE', '30'))

# Output in the expected format: "score id title"
print(f"{mock_score} 9999 Mock Joke Title")
sys.exit(0)
