"""Parser for McHawList joke emails."""

from .email_data import EmailData, JokeData
from . import register_parser


def _can_be_parsed_here(email: EmailData) -> bool:
    """
    Check if this parser can handle the email based on the From header.
    
    The parser is designed for McHawList emails from Keith Sullivan.
    
    Args:
        email: EmailData object containing email information
        
    Returns:
        bool: True if the email appears to be from McHawList, False otherwise
    """
    return "ksullivan@worldnet.att.net" in email.from_header.lower()


@register_parser(_can_be_parsed_here)
def parse(email: EmailData) -> list[JokeData]:
    """
    Parse McHawList email and extract jokes.
    
    McHawList emails contain multiple jokes separated by delimiter lines.
    Each joke has a title (first line of content) followed by content.
    
    Parameters
    ----------
    email : EmailData
        Email to parse
        
    Returns
    -------
    list[JokeData]
        List of extracted jokes in JokeData format.
    """
    # Use text format if available, otherwise html
    content = email.text if email.text.strip() else email.html
    
    if not content.strip():
        return []
    
    lines = content.split('\n')
    jokes = []
    
    # Skip initial "From:" line and blank lines to find first joke
    i = 0
    # Skip the "From: Keith Sullivan..." line and any following blank lines
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith("From:") or not line:
            i += 1
            continue
        break
    
    # Process the remaining lines looking for jokes
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip blank lines
        if not line:
            i += 1
            continue
        
        # Check for end markers
        if line.startswith("=-=-=-=-=-") or line.startswith("-----"):
            # Skip this delimiter line
            i += 1
            continue
        
        # This should be a joke title (all caps line)
        title = line.title()
        
        # Collect the joke content until next delimiter or end
        joke_lines = []
        i += 1
        
        while i < len(lines):
            line = lines[i].strip()
            
            # Check for end marker
            if line.startswith("=-=-=-=-=-") or line.startswith("-----"):
                # End of joke content
                break
            
            # Skip blank lines between jokes but preserve paragraph structure
            if not line:
                # Add blank line to separate paragraphs
                joke_lines.append("")
            else:
                joke_lines.append(line)
            
            i += 1
        
        # Process joke lines: join non-blank lines with spaces, keep blank lines between paragraphs
        if joke_lines:
            # First, remove excess blank lines (multiple consecutive blanks become one)
            processed_lines = []
            prev_was_blank = False
            for j, jline in enumerate(joke_lines):
                if not jline:
                    # This is a blank line
                    if not prev_was_blank and j > 0:
                        # Only add blank line if previous was non-blank
                        processed_lines.append("")
                        prev_was_blank = True
                    # Otherwise skip multiple blank lines
                else:
                    # Non-blank line
                    processed_lines.append(jline)
                    prev_was_blank = False
            
            # Now join non-blank lines that are part of the same paragraph
            # But since we already handled blank lines above, we just need to join lines
            # that don't have blank lines between them
            final_text = ""
            paragraph = []
            for line in processed_lines:
                if not line:
                    if paragraph:
                        final_text += " ".join(paragraph) + "\n\n"
                        paragraph = []
                else:
                    paragraph.append(line)
            
            # Add the last paragraph if any
            if paragraph:
                final_text += " ".join(paragraph)
            
            # Trim the final text and remove extra whitespace at beginning/end
            final_text = final_text.strip()
            
            if final_text:
                jokes.append(JokeData(
                    text=final_text,
                    submitter=email.from_header,
                    title=title
                ))
    
    return jokes
