"""Parser for Mikey's Funnies — see parser-hints.md."""

from .email_data import EmailData, JokeData
from . import register_parser
import logging

logging.basicConfig(level=logging.WARNING)

def _can_be_parsed_here(email: EmailData) -> bool:
    """Return True if this parser can parse the email."""
    return "funnies-owner@lists.mikeysfunnies.com" in email.from_header.lower()

@register_parser(_can_be_parsed_here)
def parse(email: EmailData) -> list[JokeData]:
    """Parse email and return a list of extracted jokes (possibly empty)."""
    jokes = []
    
    # Text format is the only format available for this parser
    if not email.text.strip():
        return []
    
    lines = email.text.split('\n')
    
    # Find start marker
    start_idx = -1
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Match "Today's Funny" or "Today's \"Funny\"" (case-insensitive)
        if stripped.lower().startswith("today's funny") or stripped.lower().startswith("today's \"funny\""):
            start_idx = i + 1  # Start after the marker line
            break
    
    # If no start marker found, return empty list
    if start_idx == -1:
        return []
    
    # Find end marker
    end_idx = -1
    for i in range(start_idx, len(lines)):
        stripped = lines[i].strip()
        if stripped.lower().startswith("today's thot"):
            end_idx = i
            break
    
    # Extract joke text
    if start_idx >= len(lines):
        return []
    
    # Collect lines between start and end markers
    joke_lines = []
    paragraph_lines = []
    
    for i in range(start_idx, end_idx if end_idx != -1 else len(lines)):
        line = lines[i]
        stripped = line.strip()
        
        if not stripped:
            # Blank line - end current paragraph
            if paragraph_lines:
                # Join paragraph lines with spaces, add double newline
                joke_lines.append(' '.join(paragraph_lines) + '\n\n')
                paragraph_lines = []
        else:
            # Non-blank line - continue current paragraph
            paragraph_lines.append(stripped)
    
    # Handle last paragraph if any
    if paragraph_lines:
        joke_lines.append(' '.join(paragraph_lines) + '\n\n')
    
    # Combine and trim
    joke_text = ''.join(joke_lines).strip()
    
    if joke_text:
        jokes.append(JokeData(
            text=joke_text,
            submitter=email.from_header,
            title=""
        ))
    
    return jokes
