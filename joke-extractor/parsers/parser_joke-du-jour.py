"""Parser for Joke du Jour emails from ladyhawke@jokedujour.com."""

from .email_data import EmailData, JokeData
from . import register_parser
import logging
import re

logging.basicConfig(level=logging.WARNING)

def _can_be_parsed_here(email: EmailData) -> bool:
    """Return True if this parser can parse the email."""
    return "ladyhawke@jokedujour.com" in email.from_header.lower()

@register_parser(_can_be_parsed_here)
def parse(email: EmailData) -> list[JokeData]:
    """Parse email and return a list of extracted jokes."""
    jokes = []
    
    # Use plain text since html_text is empty in all samples
    if not email.text.strip():
        return []
    
    lines = email.text.split('\n')
    i = 0
    submitter = email.from_header
    
    while i < len(lines):
        line = lines[i].strip()
        
        # Look for start marker: line that starts with "~*~*"
        if line.startswith('~*~*'):
            # Skip the start marker line
            i += 1
            
            # Skip blank lines
            while i < len(lines) and not lines[i].strip():
                i += 1
            
            if i >= len(lines):
                break
                
            # Next non-blank line is the title
            title_line = lines[i].strip()
            
            # Extract title from quotes if present
            title = ""
            if '"' in title_line:
                # Title might be embedded in quotes within the line
                match = re.search(r'"([^"]*)"', title_line)
                if match:
                    title = match.group(1).strip()
            
            # Check if this is actually an end marker or continuation
            # According to hints, if line starts with "<>*<>" it's end of valid content
            if line.startswith('<>*<>'):
                break
            
            joke_lines = []
            i += 1
            
            # Collect joke text until we hit an "http" line (ad starts)
            while i < len(lines):
                line = lines[i].rstrip()
                
                # Check for end of joke (starts with http for ad)
                if line.startswith('http'):
                    ad_end = line
                    # Skip the ad lines until we hit another start marker or end
                    # First, skip the ad line itself
                    i += 1
                    # Skip subsequent ad lines until we find either a start marker or non-ad line
                    while i < len(lines):
                        ad_line = lines[i].strip()
                        i += 1
                        # If we find another http line, keep skipping (ad continues)
                        if ad_line == ad_end:
                            break

                    # For now, just continue to next line
                    i += 1
                    break
                elif line.startswith('<>*<>'):
                    # End of valid content marker
                    i = len(lines)
                    break
                elif line:  # Non-empty line
                    joke_lines.append(line)
                    i += 1
                else:
                    # Blank line - this indicates paragraph separation
                    line = "\n\n"
                    joke_lines.append(line)
                    i += 1
            
            # Join joke lines
            if joke_lines:
                joke_text = ''.join(joke_lines)
                
                if joke_text:
                    jokes.append(JokeData(
                        text=joke_text,
                        submitter=submitter,
                        title=title
                    ))
        else:
            i += 1
    
    return jokes
