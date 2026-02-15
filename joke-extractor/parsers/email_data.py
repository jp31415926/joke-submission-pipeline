# shared type to pass data to and from parsers
from typing import NamedTuple

class EmailData(NamedTuple):
    """Represents email data with text content and headers."""
    text: str
    html: str
    from_header: str
    subject_header: str

class JokeData(NamedTuple):
    """Represents joke data, including the joke text, the submitter address and the joke title."""
    text: str
    submitter: str
    title: str
