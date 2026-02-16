#!/usr/bin/env python3
"""
Stage 01 - Incoming: Process emails through joke-extract.py and prepare for pipeline.
"""

import os
import shutil
import tempfile
from typing import Tuple, Dict

from stage_processor import StageProcessor
from file_utils import (
    parse_joke_file,
    generate_joke_id,
    initialize_metadata,
    atomic_move
)
from external_scripts import run_external_script
from logging_utils import get_logger
import config


class IncomingProcessor(StageProcessor):
    """
    Process emails through joke-extract.py and prepare jokes for pipeline.
    
    This stage is unique because it:
    - Processes EMAIL files (not joke files) from incoming/
    - May produce 0 or more joke files per email
    - Generates UUID for each extracted joke
    - Initializes metadata for each joke
    """
    
    def __init__(self):
        """Initialize the Incoming processor."""
        super().__init__(
            stage_name="incoming",
            input_stage=config.STAGES["incoming"],
            output_stage=config.STAGES["parsed"],
            reject_stage=config.REJECTS["parse"],
            config_module=config
        )
        self.logger = get_logger("IncomingProcessor")
    
    def process_file(
        self,
        filepath: str,
        headers: Dict[str, str],
        content: str
    ) -> Tuple[bool, Dict[str, str], str, str]:
        """
        Process an email file through joke-extract.py.
        
        Note: This method processes EMAIL files, not joke files.
        The headers and content parameters are not used as this stage
        processes raw email files.
        
        Args:
            filepath: Path to the email file
            headers: Not used (email files don't have joke headers)
            content: Not used (email files are processed by joke-extract.py)
            
        Returns:
            Tuple of (success, headers, content, reject_reason)
            - success: Always True if at least one joke extracted
            - headers: Empty dict (not applicable)
            - content: Empty string (not applicable)
            - reject_reason: Reason if no jokes extracted
        """
        # Extract email filename for metadata
        email_filename = os.path.basename(filepath)
        
        # Create temporary directories for joke-extract.py
        temp_dir = tempfile.mkdtemp(prefix="joke_extract_")
        success_dir = os.path.join(temp_dir, "success")
        fail_dir = os.path.join(temp_dir, "fail")
        os.makedirs(success_dir, exist_ok=True)
        os.makedirs(fail_dir, exist_ok=True)
        
        try:
            # Call joke-extract.py
            self.logger.info(f"Calling joke-extract.py for {email_filename}")
            return_code, stdout, stderr = run_external_script(
                config.JOKE_EXTRACTOR,
                [filepath, success_dir, fail_dir],
                timeout=60
            )
            
            # Check return code
            if return_code != 0:
                self.logger.error(
                    f"joke-extract.py failed with return code {return_code} "
                    f"for {email_filename}: {stderr}"
                )
                return (False, {}, "", f"joke-extract.py failed with return code {return_code}")
            
            # Get list of extracted jokes
            extracted_files = [
                f for f in os.listdir(success_dir)
                if os.path.isfile(os.path.join(success_dir, f))
                and not f.startswith('.')
            ]
            
            # Check if any jokes were extracted
            if not extracted_files:
                self.logger.warning(f"No jokes extracted from {email_filename}")
                return (False, {}, "", "No jokes extracted from email")
            
            # Process each extracted joke
            self.logger.info(
                f"Found {len(extracted_files)} joke(s) extracted from {email_filename}"
            )
            
            for extracted_file in extracted_files:
                self._process_extracted_joke(
                    os.path.join(success_dir, extracted_file),
                    email_filename
                )
            
            # Return success
            # Note: headers and content are empty because this stage doesn't
            # use the normal pattern (it creates multiple new files)
            return (True, {}, "", "")
            
        finally:
            # Clean up temporary directories
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                self.logger.warning(f"Failed to clean up temp directory {temp_dir}: {e}")
    
    def _process_extracted_joke(self, extracted_filepath: str, email_filename: str):
        """
        Process a single extracted joke file.
        
        Args:
            extracted_filepath: Path to the extracted joke file
            email_filename: Name of the source email file
        """
        # Read the extracted joke
        headers, content = parse_joke_file(extracted_filepath)
        
        # Generate unique Joke-ID
        joke_id = generate_joke_id()
        
        # Initialize metadata - pass the joke_id so it doesn't generate a new one
        updated_headers = headers.copy()
        updated_headers['Joke-ID'] = joke_id
        updated_headers['Source-Email-File'] = email_filename
        updated_headers['Pipeline-Stage'] = self.output_stage
        
        # Determine output directory (check priority first)
        if os.path.dirname(os.path.dirname(extracted_filepath)).startswith(
            config.PIPELINE_PRIORITY
        ):
            output_dir = os.path.join(config.PIPELINE_PRIORITY, self.output_stage)
        else:
            output_dir = os.path.join(config.PIPELINE_MAIN, self.output_stage)
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Create output filepath with UUID
        output_filepath = os.path.join(output_dir, f"{joke_id}.txt")
        
        # Write the joke file
        from file_utils import write_joke_file
        write_joke_file(output_filepath, updated_headers, content)
        
        self.logger.info(
            f"Created joke file {joke_id}.txt from {email_filename}"
        )
    
    def _move_to_output(self, filepath: str, headers: Dict[str, str], content: str):
        """
        Override the base class method.
        
        This stage doesn't use the standard move_to_output pattern
        because it creates new files instead of moving the input file.
        The input email file is simply deleted after successful processing.
        """
        # Delete the source email file
        try:
            os.remove(filepath)
            self.logger.info(f"Deleted source email file: {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to delete source email file {filepath}: {e}")
    
    def _move_to_reject(self, filepath: str, headers: Dict[str, str], content: str, reason: str):
        """
        Override the base class method to handle email files.
        
        Email files don't have joke headers, so we just move the raw email file
        to the reject directory.
        """
        # Get the email filename
        email_filename = os.path.basename(filepath)
        
        # Determine reject directory
        if filepath.startswith(config.PIPELINE_PRIORITY):
            reject_dir = os.path.join(config.PIPELINE_PRIORITY, self.reject_stage)
        else:
            reject_dir = os.path.join(config.PIPELINE_MAIN, self.reject_stage)
        
        # Create reject directory if needed
        os.makedirs(reject_dir, exist_ok=True)
        
        # Move email file to reject directory
        reject_path = os.path.join(reject_dir, email_filename)
        try:
            shutil.move(filepath, reject_path)
            self.logger.info(f"Moved rejected email {email_filename} to {reject_dir}. Reason: {reason}")
        except Exception as e:
            self.logger.error(f"Failed to move rejected email {filepath}: {e}")


def main():
    """Main entry point for running this stage standalone."""
    from logging_utils import setup_logging
    
    # Setup logging
    setup_logging(config.LOG_DIR, config.LOG_LEVEL)
    
    # Create and run processor
    processor = IncomingProcessor()
    processor.run()


if __name__ == "__main__":
    main()
