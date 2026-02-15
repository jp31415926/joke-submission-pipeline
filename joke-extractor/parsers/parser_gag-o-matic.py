"""Parser for Gag-O-Matic Joke Server — see parser-hints.md."""

from .email_data import EmailData, JokeData
from . import register_parser
import logging

# Configure logging to stderr for visibility in pipelines
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def _can_be_parsed_here(email: EmailData) -> bool:
    """Return True if this parser can parse the email."""
    return "jokes@gag-o-matic.lowcomdom.com" in email.from_header.lower()

@register_parser(_can_be_parsed_here)
def parse(email: EmailData) -> list[JokeData]:
    """Parse email and return a list of extracted jokes (possibly empty)."""
    jokes = []
    submitter = email.from_header

    # Use HTML text if available, otherwise plain text
    content = email.html.strip() if email.html.strip() else email.text.strip()
    if not content:
        return []

    # Extract title from subject, removing trailing periods
    title = email.subject_header.rstrip('.')

    # Find the end marker line
    lines = content.split('\n')

    # Find the first line that starts with "Gag-O-Matic Joke Server"
    end_index = -1
    for i, line in enumerate(lines):
        if line.startswith("Gag-O-Matic Joke Server"):
            end_index = i
            break

    # If no end marker found, use all lines
    if end_index == -1:
        end_index = len(lines)

    joke_lines = []
    prev = ''
    for i in range(0, end_index):
        line = lines[i].rstrip()
        # if we hit a blank line, add two new lines, else keep the lines long
        if not line:
            line2 = '\n\n'
        else:
            if prev:
                line2 = ' ' + line
            else:
                line2 = line
        prev = line
        joke_lines.append(line2)

    joke_text = ''.join(joke_lines) if joke_lines else ""

    # Add to jokes list
    jokes.append(JokeData(
        text=joke_text,
        submitter=submitter,
        title=title
    ))

    return jokes
