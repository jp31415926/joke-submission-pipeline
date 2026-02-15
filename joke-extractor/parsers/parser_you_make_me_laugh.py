"""Parser for 'You Make Me Laugh' (CrosswalkMail) format."""

from .email_data import EmailData, JokeData

from . import register_parser
import logging

# Configure logging to stderr for visibility in pipelines
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def _can_be_parsed_here(email: EmailData) -> bool:
    return "crosswalk@crosswalkmail.com" in email.from_header.lower()
    #return False

@register_parser(_can_be_parsed_here)

def parse(email: EmailData) -> list[JokeData]:
    """
    Parse the "You Make Me Laugh" email format.

    This parser expects a subject like "Acts 2:38 - August 26, 2010", extracts the scripture reference,
    and isolates the joke content between a visual separator line (`__________`) and the footer marker
    `cybersalt.org/cleanlaugh`.

    Parameters
    ----------
    email : EmailData
        Email to parse
        
    Returns
    -------
    list[JokeData]
        List of extracted jokes in JokeData.
    """
    # storage for all the jokes that are collected. This is the return variable
    jokes = []

    joke_submitter = email.from_header
    joke_text = ''

    # Extract subject without date (e.g., "Acts 2:38 - August 26, 2010" → "Acts 2:38")
    sub_parts = email.subject_header.split('-')
    joke_title = ''.join(sub_parts[:-1]).strip()

    lines = []
    if len(email.html) > 0:
        lines = email.html.split('\n')
    else:
        lines = email.text.split('\n')

    # Find visual separator line: starts with "__________" (10 underscores)
    bar_index = None
    for i, line in enumerate(lines):
        if line.strip().startswith('__________'):
            bar_index = i
            break

    if bar_index is None:
        return jokes

    # Skip 2 lines after the bar
    i = bar_index + 2
    if i >= len(lines):
        return jokes

    # Skip "Newsletters" line and next blank line if present
    line_parts = lines[i].split()
    if line_parts and line_parts[-1] == "Newsletters":
        i += 2
        if i >= len(lines):
            return jokes

    # Skip the line matching cleaned subject (if present)
    line = lines[i]
    if line == joke_title:
        i += 1
        if i >= len(lines):
            return jokes
        line = lines[i].strip()

    # Collect content until reaching footer marker
    while i < len(lines) and line != "cybersalt.org/cleanlaugh":
        if not line.startswith("*"):
            joke_text += line + "\n\n"
        i += 1
        if i < len(lines):
            line = lines[i]
        else:
            line = ""

    if joke_text:
        jokes.append(JokeData(text=joke_text.strip(), submitter=joke_submitter, title=joke_title))

    return jokes
