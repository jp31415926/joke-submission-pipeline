"""Parser for Crosswalk - You Make Me Laugh."""

from .email_data import EmailData, JokeData
from . import register_parser
import re

import logging
# Configure logging to stderr for visibility in pipelines
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def _can_be_parsed_here(email: EmailData) -> bool:
    """Return True if this parser can parse the email."""
    return "you_make_me_laugh@lists.crosswalk.com" in email.from_header.lower()


@register_parser(_can_be_parsed_here)
def parse(email: EmailData) -> list[JokeData]:
    """Parse email and return a list of extracted jokes."""
    jokes = []
    
    # Prefer pre-processed HTML text, fall back to text
    content = email.html.strip() if email.html.strip() else email.text.strip()
    if not content:
        return []
    
    lines = content.split('\n')
    
    # Extract title from subject line
    subject = email.subject_header
    # Pattern: "Crosswalk - You Make Me Laugh: "Title", Date"
    match = re.match(r'Crosswalk - You Make Me Laugh: "([^"]+)", .+', subject)
    if not match:
        return []
    
    title = match.group(1)
    start_marker = f"*{title}*"
    
    # Find the start marker
    start_idx = None
    for i, line in enumerate(lines):
        if line.strip() == start_marker:
            start_idx = i + 1
            break
    
    if start_idx is None:
        return []
    
    # Collect joke text until end marker
    joke_lines = []
    for i in range(start_idx, len(lines)):
        line = lines[i].strip()
        # End marker is line containing "cybersalt.org/cleanlaugh"
        if "cybersalt.org/cleanlaugh" in line.lower():
            break
        if not line:
            line = '\n\n'
        joke_lines.append(line)
    
    # Remove the last line if it has asterisks on both sides
    if joke_lines and joke_lines[-1].startswith('*') and joke_lines[-1].endswith('*'):
        joke_lines = joke_lines[:-1]
    
    # Join the joke text with newlines between lines
    joke_text = ''.join(joke_lines).strip()
    
    if joke_text:
        jokes.append(JokeData(
            text=joke_text,
            submitter=email.from_header,
            title=title
        ))
    
    return jokes
