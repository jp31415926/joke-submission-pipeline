"""Parser for Steve Sanderson's 'Sunday Fun Stuff' emails."""

from .email_data import EmailData, JokeData

import logging
# Configure logging to stderr for visibility in pipelines
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

from . import register_parser

def _can_be_parsed_here(email: EmailData) -> bool:
    #return False
    return "aardvark@illinois.edu" in email.from_header

@register_parser(_can_be_parsed_here)

def parse(email: EmailData) -> list[JokeData]:
    """
    Parse Steve Sanderson's "Sunday Fun Stuff" email format.

    This parser identifies jokes delimited by:
    - Start marker: `*` repeated =10 times (`**********`)
    - Title: a line ending with `:`
    - Joke body: lines up until the next `[...]:`-style closing tag (e.g., `[end]`)
    - Ends at a line containing exactly `Steve Sanderson`

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

    joke_submitter = "Steve C Sanderson <aardvark@illinois.edu>"
    joke_text = ''
    joke_title = ''

    i = 0
    state = 0
    lines = []
    if len(email.html) > 0:
        lines = email.html.split('\n')
    else:
        lines = email.text.split('\n')

    # State machine for parsing:
    # 0: wait for "*..." line (start of joke block)
    # 1: skip blank lines, then expect title (ends with ':')
    # 2: skip blank line before joke body
    # 3: collect lines until closing tag (e.g., `[end]`)
    while i < len(lines):
        line = lines[i]
        #logging.info(f"state {state}: {line}")

        match state:
            case 0:  # Wait for start delimiter
                if line.startswith('*' * 10):  # e.g., "**********"
                    state = 1
                i += 1

            case 1:  # Find title (line ending with ':')
                if not line:
                    i += 1
                elif line.endswith(':'): # first line ends with colon is not part of the joke, so skip it
                    state = 2
                    i += 1
                elif line == line.upper():
                    state = 2
                    # convert to title capitization
                    joke_title = line.title()
                    i += 1
                elif line == 'Steve Sanderson':
                    # End of content
                    i = len(lines)
                else:
                    # No title found, jump to content (non-standard)
                    state = 3

            case 2:  # Skip blank line before joke body
                if not line:
                    i += 1
                state = 3

            case 3:  # Collect until end marker `[...]`
                if (line.startswith('[') and line.endswith(']')) or line == 'Steve Sanderson' or \
                        line.startswith("Mikey's Funnies") or line.startswith("A Joke A Day") or \
                        line.startswith("The Good Clean Fun List"):
                    if joke_text:
                        jokes.append(JokeData(text=joke_text.strip(), submitter=joke_submitter, title=joke_title))
                    if line == 'Steve Sanderson':
                        break
                    joke_text = ""
                    joke_title = ""
                    state = 1
                    i += 1
                else:
                    if line:
                        joke_text += line + "\n\n"
                    i += 1

    return jokes
