#!/usr/bin/env python3
"""
Mock joke-extract.py for testing purposes.

This script simulates the behavior of the real joke-extract.py:
- Takes success_dir, fail_dir, and email file as arguments
- Extracts jokes from the email and writes them to success_dir
- Returns 0 on success, non-zero on failure
"""

import sys
import os


def extract_jokes(email_path, success_dir, fail_dir):
    """Extract jokes from email file."""
    # Read the email file
    with open(email_path, 'r', encoding='iso-8859-1') as f:
        email_content = f.read()
    
    # Get the email filename
    email_filename = os.path.basename(email_path)
    
    # Simulate different behaviors based on email filename
    if 'single_joke' in email_filename:
        # Create a single joke file
        joke_content = """Title: Colorful Meal
Submitter: "'Thomas S. Ellsworth' tellswor@kcbx.net [good-clean-fun]" <good-clean-fun-noreply@yahoogroups.com>

Over dinner, I explained the health benefits of a colorful meal to my family. "The more colors, the more variety of nutrients," I told them. Pointing to our food, I asked, "How many different colors do you see?"

"Six," volunteered my daughter. "Seven if you count the burned parts."
"""
        joke_file = os.path.join(success_dir, 'joke1.txt')
        with open(joke_file, 'w', encoding='utf-8') as f:
            f.write(joke_content)
        return 0
    
    elif 'multiple_jokes' in email_filename:
        # Create multiple joke files
        joke1_content = """Title: Atoms
Submitter: "'Jane Smith' jsmith@example.com [good-clean-fun]" <good-clean-fun-noreply@yahoogroups.com>

Why don't scientists trust atoms?

Because they make up everything!
"""
        joke2_content = """Title: Gummy Bear
Submitter: "'Jane Smith' jsmith@example.com [good-clean-fun]" <good-clean-fun-noreply@yahoogroups.com>

What do you call a bear with no teeth?

A gummy bear!
"""
        joke1_file = os.path.join(success_dir, 'joke1.txt')
        joke2_file = os.path.join(success_dir, 'joke2.txt')
        
        with open(joke1_file, 'w', encoding='utf-8') as f:
            f.write(joke1_content)
        with open(joke2_file, 'w', encoding='utf-8') as f:
            f.write(joke2_content)
        return 0
    
    elif 'no_jokes' in email_filename:
        # No jokes found - return success but create no files
        return 0
    
    elif 'fail' in email_filename or 'error' in email_filename:
        # Simulate failure
        return 1
    
    else:
        # Default: create a generic joke
        joke_content = """Title: Test Joke
Submitter: "Test User" <test@example.com>

This is a test joke.
"""
        joke_file = os.path.join(success_dir, 'joke1.txt')
        with open(joke_file, 'w', encoding='utf-8') as f:
            f.write(joke_content)
        return 0


def main():
    """Main entry point."""
    if len(sys.argv) != 4:
        print("Usage: joke-extract.py <success_dir> <fail_dir> <email_file>", file=sys.stderr)
        sys.exit(1)

    success_dir = sys.argv[1]
    fail_dir = sys.argv[2]
    email_path = sys.argv[3]

    # Check that email file exists
    if not os.path.exists(email_path):
        print(f"Error: Email file not found: {email_path}", file=sys.stderr)
        sys.exit(1)
    
    # Extract jokes
    exit_code = extract_jokes(email_path, success_dir, fail_dir)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
