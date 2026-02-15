"""Parser for Humor_G emails — see parser-hints.md."""

from .email_data import EmailData, JokeData
from . import register_parser
import logging
import re

logging.basicConfig(level=logging.WARNING)

def _can_be_parsed_here(email: EmailData) -> bool:
    """Return True if this parser can parse the email."""
    # Check if the email is from the Humor_G source
    return "judib51@comcast.net" in email.from_header.lower()

@register_parser(_can_be_parsed_here)
def parse(email: EmailData) -> list[JokeData]:
    """Parse email and return a list of extracted jokes (possibly empty)."""
    jokes = []
    submitter = email.from_header
    
    # Check subject for discard conditions
    subject_lower = email.subject_header.lower()
    if "toon" in subject_lower or "good ole maxine" in subject_lower or "attachment" in subject_lower:
        return []
    
    # Prefer HTML format if available, otherwise use plain text
    if email.html.strip():
        lines = email.html.split('\n')
    else:
        lines = email.text.split('\n')
    
    # Find the joke content
    # The joke starts at the first non-blank line
    joke_lines = []
    end_marker_found = False
    
    for i, line in enumerate(lines):
        stripped = line.strip()
        
        # Check for end marker (starts with 10+ tildes)
        if stripped.startswith('~' * 10):
            end_marker_found = True
            break
            
        # Add line to joke content
        joke_lines.append(stripped)
    
    # If no end marker found, log warning but continue
    if not end_marker_found and joke_lines:
        logging.warning("No end marker found in Humor_G email, extracted to EOF")
    
    # If we have joke lines, process them
    if not joke_lines:
        return []
    
    # Check for forbidden content
    full_joke_text = '\n'.join(joke_lines)
    if '[cid:' in full_joke_text.lower() or 'http' in full_joke_text.lower():
        return []
    
    # Format the joke text properly
    # For HTML format: preserve paragraph breaks (lines separated by blank lines become paragraphs)
    # For text format: join lines with spaces if no blank line between, but use \n\n for paragraph breaks
    
    # First, split into paragraphs (lines separated by blank lines in the original)
    # Since we stripped lines, we need to reconstruct paragraphs
    paragraphs = []
    current_paragraph = []
    
    for line in joke_lines:
        # In the original content, blank lines would have been empty strings
        # Since we stripped them, we need to check if consecutive lines should be joined
        if line.strip():
            current_paragraph.append(line.strip())
        else:
            if current_paragraph:
                paragraphs.append(current_paragraph)
                current_paragraph = []
    
    if current_paragraph:
        paragraphs.append(current_paragraph)
    
    # If we only have one paragraph (common case in these emails), join lines with spaces
    # If multiple paragraphs, join within paragraph with space, between paragraphs with \n\n
    joke_text_parts = []
    for para in paragraphs:
        # Join lines in paragraph with space
        para_text = ' '.join(para)
        joke_text_parts.append(para_text)
    
    # Join paragraphs with \n\n (but since we likely only have one paragraph, just use the text)
    joke_text = '\n\n'.join(joke_text_parts)
    
    # Clean up any remaining extra whitespace
    joke_text = joke_text.strip()
    
    # Create the JokeData
    joke = JokeData(
        text=joke_text,
        submitter=submitter,
        title=""
    )
    
    jokes.append(joke)
    
    return jokes
