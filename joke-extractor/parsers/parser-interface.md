# Parser Function Interface
- Use the exact name, input parameter names and types, and return types provided for the functions `_can_be_parsed_here(email: EmailData) -> bool` and `parse(email: EmailData) -> list[JokeData]`.

- The definition of `class EmailData` and `class JokeData` are provided by the `email_data.py` file. It is also provided here for reference.

```python
from typing import NamedTuple

class EmailData(NamedTuple):
    """Represents email data with text & HTML content and from/subject headers."""
    text: str
    html: str
    from_header: str
    subject_header: str

class JokeData(NamedTuple):
    """Represents joke data, including the joke text, the submitter address and the joke title."""
    text: str
    submitter: str
    title: str
```

- The `_can_be_parsed_here(email: EmailData)` function, typically uses `email.from_header` to determine if the email is recognized as an email that can be parsed with this parser.

# Sample Input Email File Format
The sample email files provided give you all the data that would be contained in the `email: EmailData` parameter in JSON format. An example of this follows. This is only provided so you can analysis a subset of the email content to find the parser logic.

```json
{
  "subject": "Best of Humor July 13th",
  "from": "\"Bestofhumor.com\" <shawn@bestofhumor.com>",
  "plain_text": "Content of plain text part of the email.\nFunny!\n",
  "html_text": "<p>Content of plain text part of the email.<br>\nFunny!</p>\n"
}
```
