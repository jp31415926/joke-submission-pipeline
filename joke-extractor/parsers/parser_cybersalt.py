"""Parser for Cybersalt Digest emails — extracts jokes from CleanLaugh sections."""

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
    return "posts@cybersaltlists.org" in email.from_header.lower()

@register_parser(_can_be_parsed_here)
def parse(email: EmailData) -> list[JokeData]:
    """Parse email and return a list of extracted jokes (possibly empty)."""
    jokes = []
    
    # Prefer HTML text as per hints and spec
    content = email.html.strip() if email.html.strip() else email.text.strip()
    if not content:
        return []
    
    lines = content.split('\n')
    
    submitter = email.from_header
    
    # Find the start delimiter: "Here is today's CleanLaugh"
    start_marker = "Here is today's CleanLaugh"
    end_marker = "You can rate this joke at:"
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Check if this line starts with the start marker
        if line.startswith(start_marker):
            # Extract title
            title = ""
            
            # Remove the start marker to get the rest of the line
            rest = line[len(start_marker):].strip()
            
            # Try to extract title: it's after " - " and possibly quoted
            # Pattern: "Here is today's CleanLaugh. - Title" or "Here is today's CleanLaugh - Title"
            # The title might be in quotes like "- \"Title\"" or "- Title"
            
            if rest.startswith("-"):
                rest = rest[1:].strip()
                
                # Check if title is in quotes
                if rest.startswith('"') and rest.endswith('"'):
                    title = rest[1:-1]  # Remove quotes
                elif rest.startswith("'") and rest.endswith("'"):
                    title = rest[1:-1]  # Remove single quotes
                else:
                    title = rest
                
                # Clean up title - remove any trailing punctuation that might not belong
                title = title.strip()
            elif rest:
                # If there's content after the marker but no dash, treat whole thing as title
                title = rest.strip()
            
            # Now collect joke text until end marker
            joke_lines = []
            i += 1
            while i < len(lines):
                current_line = lines[i].strip()
                
                # Check for end marker
                if current_line.startswith(end_marker):
                    break
                
                # Add non-empty lines to joke text
                if current_line:
                    joke_lines.append(current_line)
                
                i += 1
            
            # Join joke lines with double newlines as per spec
            if joke_lines:
                joke_text = '\n\n'.join(joke_lines).strip()
                if joke_text:
                    jokes.append(JokeData(
                        text=joke_text,
                        submitter=submitter,
                        title=title
                    ))
            
            # Since only one joke per email, return immediately
            return jokes
        
        i += 1
    
    # If no start marker found, return empty list
    return []
