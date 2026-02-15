"""Parser for Christian Voices joke emails."""

from .email_data import EmailData, JokeData

from . import register_parser

def _can_be_parsed_here(email: EmailData) -> bool:
    """
    Check if this parser can handle the email based on the From header.
    
    The parser is designed for emails from "Christian Voice" newsletter,
    which uses email addresses containing "comcast.net" and "GrampsTN".
    
    Args:
        from_header (str): The raw From: header value (without "From: " prefix)
        
    Returns:
        bool: True if the email appears to be from Christian Voices, False otherwise
    """
    # Christian Voices emails typically have "GrampsTN" or "CVWorldwide" in the address
    # The from_header contains email addresses in formats like:
    # "Christian Voice <GrampsTN@comcast.net>" or "Bob <CVWorldwide@wmconnect.com>"
    # We look for consistent identifiers across the sample emails
    return False
    #return "GrampsTN@comcast.net" in email.from_header or "Christian Voice" in email.from_header


@register_parser(_can_be_parsed_here)
def parse(email: EmailData) -> list[JokeData]:
    """
    Parse Christian Voices email format to extract jokes.
    
    This parser identifies jokes from the "Christian Voices" email newsletter.
    Joke sections are marked with a line containing exactly "HUMOR" and continue
    until the next "<>< " delimited section.
    
    The  is ignored as it doesn't describe the individual jokes.
    
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

    # Initialize results
    # Get the From header value (as required by the interface)
    joke: JokeData
    joke_submitter = email.from_header
    joke_title = ''
    joke_text = ''

    # Split into lines for processing
    lines = []
    if len(email.html) > 0:
        lines = email.html.split('\n')
    else:
        lines = email.text.split('\n')
    
    # State machine to process the content
    # We'll iterate through lines looking for the HUMOR section
    i = 0
    
    # State machine states:
    # 0: Initial state, looking for HUMOR line
    # 1: Found HUMOR, looking for title (next non-blank line)
    # 2: Collecting joke content until <>< delimiter
    state = 0

    while i < len(lines):
        line = lines[i]
        
        match state:
            case 0:  # Looking for HUMOR line
                # HUMOR line is exactly "HUMOR"
                if line.startswith("HUMOR"):
                    state = 1
                i += 1
                
            case 1:  # Next non-blank line is the title if ≤35 characters
                if not line:  # Skip blank lines
                    i += 1
                    continue
                # Check if line is ≤35 characters
                if len(line) <= 35:
                    joke_title = line.title()
                    i += 1
                else:
                    joke_title = ""  # Line too long, no title
                
                # Start collecting joke content from next line
                state = 2
                # Continue processing this line in next state
                
            case 2:  # Collecting joke content until <>< delimiter
                # Check if this line starts the delimiter "<>< "
                if line.startswith("<>< "):
                    # Finalize and save the joke
                    if joke_text:
                        jokes.append(JokeData(text=joke_text.strip(), submitter=joke_submitter, title=joke_title))

                    # for this parser, we always no more than one joke, so we are done
                    joke_text = ""
                    break
                else:
                    # Add line to current joke content
                    if line.strip() and not (line.startswith("…") or line.startswith(".")):
                        joke_text += line + "\n\n"
                
                i += 1
    
    # If no jokes were found, return empty list
    return jokes
