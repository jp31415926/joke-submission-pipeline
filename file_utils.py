#!/usr/bin/env python3
"""
File utilities for parsing and writing joke file headers and content.
"""

import os
import re
import shutil
import uuid
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


def atomic_write(target_path: str, headers_dict: Dict[str, str], content: str) -> bool:
    """
    Write a joke file atomically using tmp/ subdirectory.
    
    Args:
        target_path: Full path where the file should be written
        headers_dict: Dictionary of headers to write
        content: Joke content to write
        
    Returns:
        True on success
        
    Raises:
        Exception: If write fails for any reason
    """
    # Extract directory from target_path
    target_dir = os.path.dirname(target_path)
    
    # Create tmp/ subdirectory if it doesn't exist
    tmp_dir = os.path.join(target_dir, 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)
    
    # Generate temporary filename in tmp/
    temp_filename = f"{uuid.uuid4().hex}.txt"
    temp_path = os.path.join(tmp_dir, temp_filename)
    
    # Write file to temporary location using write_joke_file
    write_joke_file(temp_path, headers_dict, content)
    
    # Move temporary file to target_path using os.rename (atomic on same filesystem)
    os.rename(temp_path, target_path)
    
    return True


def atomic_move(source_path: str, dest_dir: str) -> str:
    """
    Move a joke file atomically using tmp/ subdirectory.
    
    Args:
        source_path: Path to source file
        dest_dir: Destination directory
        
    Returns:
        Destination path on success
        
    Raises:
        Exception: If move fails for any reason
    """
    # Verify source_path exists
    if not os.path.exists(source_path):
        raise FileNotFoundError(f"Source file does not exist: {source_path}")
    
    # Extract filename from source_path
    filename = os.path.basename(source_path)
    
    # Create dest_dir if it doesn't exist
    os.makedirs(dest_dir, exist_ok=True)
    
    # Create tmp/ subdirectory in dest_dir if it doesn't exist
    tmp_dir = os.path.join(dest_dir, 'tmp')
    os.makedirs(tmp_dir, exist_ok=True)
    
    # Copy source to dest_dir/tmp/<filename>
    temp_path = os.path.join(tmp_dir, filename)
    shutil.copy2(source_path, temp_path)
    
    # Move from dest_dir/tmp/<filename> to dest_dir/<filename> using os.rename
    dest_path = os.path.join(dest_dir, filename)
    os.rename(temp_path, dest_path)
    
    # Delete source file only after successful move
    os.remove(source_path)
    
    return dest_path


def safe_cleanup(filepath: str):
    """
    Safely remove a file if it exists.
    
    Args:
        filepath: Path to file to delete
    """
    # Check if filepath exists
    if os.path.exists(filepath):
        # If exists, delete it
        try:
            os.remove(filepath)
            # Log deletion using print (proper logging in Step 4)
            print(f"Deleted file: {filepath}")
        except Exception as e:
            # Handle errors gracefully (don't raise if file doesn't exist)
            print(f"Error deleting file {filepath}: {e}")


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


def generate_joke_id() -> str:
    """
    Generate a unique UUID for a joke.
    
    Returns:
        UUID string in format "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    """
    return str(uuid.uuid4())


def initialize_metadata(headers: Dict[str, str], email_filename: str, stage_name: str) -> Dict[str, str]:
    """
    Initialize metadata fields for a joke file.
    
    Args:
        headers: Existing headers dictionary
        email_filename: Name of the source email file
        stage_name: Name of the pipeline stage
        
    Returns:
        Updated headers dictionary with metadata fields
    """
    # Create a copy to avoid modifying the original
    updated_headers = headers.copy()
    
    # Add Joke-ID if not present (don't overwrite existing)
    if 'Joke-ID' not in updated_headers:
        updated_headers['Joke-ID'] = generate_joke_id()
    
    # Add Source-Email-File
    updated_headers['Source-Email-File'] = email_filename
    
    # Add Pipeline-Stage
    updated_headers['Pipeline-Stage'] = stage_name
    
    return updated_headers