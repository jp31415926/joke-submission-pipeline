"""Parser for Thomas S. Ellsworth emails — extract jokes from Good Clean Fun emails."""

from .email_data import EmailData, JokeData
from . import register_parser

def _can_be_parsed_here(email: EmailData) -> bool:
    """Return True if this parser can parse the email."""
    return "tellswor@kcbx.net" in email.from_header.lower()
    #return False


@register_parser(_can_be_parsed_here)
def parse(email: EmailData) -> list[JokeData]:
    """Parse email and return a list of extracted jokes (one per email, max)."""
    jokes = []
    submitter = email.from_header

    # Get subject for title (from hints: "Use email.subject_header as the title. Remove the prefix 'GCF: '.")
    raw_subject = email.subject_header or ""
    if raw_subject.startswith("GCF: "):
        title = raw_subject[5:]  # Remove "GCF: " prefix
    else:
        title = raw_subject

    # Prefer text (as per hints: "Text format is the only format available")
    lines = email.text.split('\n') if email.text.strip() else []

    # Find start delimiter: line that starts with "----------" (exactly 10 dashes)
    start_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("----------"):
            start_idx = i + 1
            break

    if start_idx == -1:
        return []  # No start delimiter → return empty list

    # Next non-blank line after start delimiter should be the repeated subject line ("GCF: ...")
    # Skip it if it matches the subject (or its "GCF: " version) exactly
    while lines[start_idx].strip() == "":
        start_idx = start_idx + 1
    if lines[start_idx].strip().startswith("GCF: "):
        start_idx = start_idx + 1

    # Now collect lines until end delimiter (another "----------")
    joke_lines = []
    prev = ''
    for i in range(start_idx + 1, len(lines)):
        line = lines[i].rstrip()
        if line.startswith("----------"):
            break
        if not line:
            joke_lines.append('\n\n')
        else:
            joke_lines.append((' ' + line) if prev else line)
        prev = line

    joke_text = ''.join(joke_lines).strip() if joke_lines else ""

    # If we found a joke, create JokeData
    if joke_text:
        jokes.append(JokeData(
            text=joke_text,
            submitter=submitter,
            title=title
        ))

    return jokes
