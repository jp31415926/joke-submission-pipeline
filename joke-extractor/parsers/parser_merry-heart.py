"""Parser for Merry Hearts joke emails."""

import re
from .email_data import EmailData, JokeData
from . import register_parser


def _can_be_parsed_here(email: EmailData) -> bool:
    """
    Check if this parser can handle the email based on the From header.
    
    Merry Hearts emails come from Timothy Anger with address tanger@lvbaptist.org.
    
    Args:
        email (EmailData): Email to check
        
    Returns:
        bool: True if the email appears to be from Merry Hearts, False otherwise
    """
    return "tanger@lvbaptist.org" in email.from_header.lower()


@register_parser(_can_be_parsed_here)
def parse(email: EmailData) -> list[JokeData]:
    """
    Parse Merry Hearts email to extract jokes.
    
    Merry Hearts emails have a standard format:
    - Header: "======..." and "A M E R R Y H E A R T"
    - Title line
    - Start marker: "-----..." or "*:-.,_,.-:*'``'*:-.,_,.-:*'``'*:-.,_,.-:*'``'"
    - Joke content
    - End marker: "======..."
    
    Parameters
    ----------
    email : EmailData
        Email to parse
        
    Returns
    -------
    list[JokeData]
        List of extracted jokes in JokeData.
    """
    jokes = []
    
    # Get the content to parse
    content = email.html if email.html.strip() else email.text
    if not content.strip():
        return []
    
    # Extract title from subject header (remove "[merry-hearts] " prefix)
    subject = email.subject_header
    if subject.startswith("[merry-hearts] "):
        title = subject[len("[merry-hearts] "):].strip()
    else:
        title = subject.strip()
    
    # Split into lines
    lines = content.split('\n')
    
    # State machine to process the content
    i = 0
    
    # Constants for markers
    START_MARKER_PATTERNS = [
        lambda line: line.startswith("-----"),
        lambda line: line.startswith("*:-.,_,.-:*'``'")
    ]
    END_MARKER = "=========="
    
    # Skip header lines until we find the first title
    # Look for lines that contain "MERRY" and "HEART" in the header
    while i < len(lines):
        if "MERRY" in lines[i].upper() and "HEART" in lines[i].upper():
            # Found the header, next line should be the title
            i += 1
            break
        i += 1
    
    # Now process the content looking for jokes
    while i < len(lines):
        # Skip blank lines
        while i < len(lines) and not lines[i].strip():
            i += 1
            
        if i >= len(lines):
            break
            
        line = lines[i]
        
        # Check if this line is a start marker
        is_start_marker = False
        for pattern in START_MARKER_PATTERNS:
            if pattern(line):
                is_start_marker = True
                break
        
        if is_start_marker:
            # We found a start marker, but we need the title that came before it
            # Use the last non-blank line before this marker as title
            # or fall back to the subject title
            prev_i = i - 1
            local_title = title  # Default to subject title
            while prev_i >= 0 and not lines[prev_i].strip():
                prev_i -= 1
                
            # If we found a non-blank line before the marker and it's not too long
            if prev_i >= 0 and len(lines[prev_i].strip()) <= 35:
                local_title = lines[prev_i].strip().title()
            
            # Start collecting joke content
            joke_lines = []
            i += 1  # Move past the start marker
            
            # Collect lines until end marker
            while i < len(lines):
                line = lines[i]
                
                # Check if this is the end marker
                if line.startswith(END_MARKER):
                    # End of this joke
                    break
                
                # Add line to joke content
                if line.strip():
                    joke_lines.append(line.strip())
                
                i += 1
            
            # Process joke lines
            if joke_lines:
                # Join lines with \n\n to create paragraphs (each line is a paragraph)
                joke_text = "\n\n".join(joke_lines)
                
                # Reduce multiple consecutive blank lines to one blank line
                # We already have single lines, so we need to handle this for any cases
                # where there might be multiple blank lines
                joke_text = re.sub(r'\n\n\n+', '\n\n', joke_text)
                
                jokes.append(JokeData(
                    text=joke_text.strip(),
                    submitter=email.from_header,
                    title=local_title
                ))
            
            # Move past the end marker
            i += 1
        else:
            # Not a start marker, skip this line
            i += 1
    
    return jokes
