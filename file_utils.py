#!/usr/bin/env python3
"""
File utilities for parsing and writing joke file headers and content.
"""

import os
import re
from typing import Tuple, Dict, List

def parse_joke_file(filepath: str) -> Tuple[Dict[str, str], str]:
    """
    Parse a joke file and return headers and content.
    
    Args:
        filepath: Path to the joke file
        
    Returns:
        Tuple of (headers_dict, content_string)
        
    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If file format is malformed
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Joke file not found: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except UnicodeDecodeError:
        # Try with ISO-8859-1 encoding as specified in instructions
        with open(filepath, 'r', encoding='iso-8859-1') as f:
            lines = f.readlines()
    
    headers = {}
    content_lines = []
    header_section_done = False
    
    for line in lines:
        # Strip line ending
        line = line.rstrip('\r\n')
        
        # Empty line indicates end of headers
        if not line:
            header_section_done = True
            # Special handling for the initial empty line (between headers and content)
            if not content_lines:
                continue
            content_lines.append(line)  # Preserve the empty line if it's part of content
            continue
            
        # If we're in the header section
        if not header_section_done:
            # Check if it's a header line (key: value format)
            if ':' in line:
                key, value = line.split(':', 1)
                headers[key.strip()] = value.strip()
            else:
                # If we encounter something that isn't a header in header section,
                # we assume this is the start of the content
                # This handles files with no headers (joke-extract.py format)
                header_section_done = True
                content_lines.append(line)
        else:
            # We're in content section
            content_lines.append(line)
    
    # Join all content lines
    content = '\n'.join(content_lines)
    
    # Remove trailing empty lines from content
    content = content.rstrip('\n')
    
    return (headers, content)


def write_joke_file(filepath: str, headers_dict: Dict[str, str], content: str):
    """
    Write a joke file with headers and content.
    
    Args:
        filepath: Path to the joke file
        headers_dict: Dictionary of headers to write
        content: Joke content to write
    """
    # Ensure trailing newline in content
    if content and not content.endswith('\n'):
        content += '\n'
    
    # Write to file
    with open(filepath, 'w', encoding='utf-8') as f:
        # Write headers
        for key, value in headers_dict.items():
            f.write(f"{key}: {value}\n")
        
        # Write blank line separator
        f.write('\n')
        
        # Write content
        f.write(content)


def validate_headers(headers_dict: Dict[str, str], required_fields: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that all required fields are present and not empty.
    
    Args:
        headers_dict: Dictionary of headers to validate
        required_fields: List of required field names
        
    Returns:
        Tuple of (is_valid, missing_fields_list)
    """
    missing_fields = []
    
    for field in required_fields:
        if field not in headers_dict:
            missing_fields.append(field)
        elif not headers_dict[field]:
            missing_fields.append(field)
    
    return (len(missing_fields) == 0, missing_fields)