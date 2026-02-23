#!/usr/bin/env python3
"""
Base class for all pipeline stage processors with retry logic and priority handling.
"""

import os
import shutil
from abc import ABC, abstractmethod
from typing import Tuple, Dict, List
from logging import Logger

from file_utils import parse_joke_file, atomic_write, atomic_move
from logging_utils import get_logger
import config


class StageProcessor(ABC):
    """
    Abstract base class for all pipeline stage processors.
    
    This class handles the common logic for:
    - Processing files in priority and main pipelines
    - Retry logic for failed processing
    - Atomic file moves
    - Logging
    """
    
    def __init__(self, stage_name: str, input_stage: str, output_stage: str, 
                 reject_stage: str, config_module):
        """
        Initialize the stage processor.
        
        Args:
            stage_name: Name of the stage (e.g., "parsed")
            input_stage: Input stage directory name (e.g., "incoming")
            output_stage: Output stage directory name (e.g., "deduped")
            reject_stage: Reject stage directory name (e.g., "rejected_duplicate")
            config_module: Configuration module
        """
        self.stage_name = stage_name
        self.input_stage = input_stage
        self.output_stage = output_stage
        self.reject_stage = reject_stage
        self.config = config_module
        self.logger = get_logger("StageProcessor")
        
    @abstractmethod
    def process_file(self, filepath: str, headers: Dict[str, str], content: str) -> Tuple[bool, Dict[str, str], str, str]:
        """
        Process a single joke file. This method must be implemented by subclasses.
        
        Args:
            filepath: Path to the joke file
            headers: Dictionary of headers from the joke file
            content: Joke content
            
        Returns:
            Tuple of (success: bool, updated_headers: dict, updated_content: str, reject_reason: str)
            reject_reason only used if success is False
        """
        pass
    
    def run(self):
        """
        Run the stage processor on all files in the priority and main pipelines.
        """
        # Process priority pipeline first
        priority_input_dir = os.path.join(self.config.PIPELINE_PRIORITY, self.input_stage)
        if os.path.exists(priority_input_dir):
            self.logger.debug(f"Starting processing of priority pipeline files in {priority_input_dir}")
            self._process_files_in_directory(priority_input_dir)
            self.logger.debug(f"Completed processing of priority pipeline files in {priority_input_dir}")
            
        # Then process main pipeline
        main_input_dir = os.path.join(self.config.PIPELINE_MAIN, self.input_stage)
        if os.path.exists(main_input_dir):
            self.logger.debug(f"Starting processing of main pipeline files in {main_input_dir}")
            self._process_files_in_directory(main_input_dir)
            self.logger.debug(f"Completed processing of main pipeline files in {main_input_dir}")
    
    def _process_files_in_directory(self, input_dir: str):
        """
        Process all files in a given input directory, oldest first.

        Args:
            input_dir: Path to the input directory
        """
        # Collect all eligible files with their modification times
        file_entries: List[Tuple[float, str]] = []
        for root, dirs, files in os.walk(input_dir):
            # Skip tmp directories
            dirs[:] = [d for d in dirs if d != 'tmp']

            for filename in files:
                if filename == '.DS_Store' or filename.startswith('.'):
                    continue
                filepath = os.path.join(root, filename)
                try:
                    mtime = os.path.getmtime(filepath)
                except OSError:
                    mtime = 0.0
                file_entries.append((mtime, filepath))

        # Process oldest files first
        file_entries.sort(key=lambda e: e[0])

        for _, filepath in file_entries:
            # Check for ALL_STOP file before processing each file
            if os.path.exists(self.config.ALL_STOP):
                self.logger.warning(f"ALL_STOP file detected at {self.config.ALL_STOP}. Exiting gracefully.")
                return

            self._process_with_retry(filepath)
    
    def _process_with_retry(self, filepath: str):
        """
        Process a file with retry logic.

        Args:
            filepath: Path to the joke file
        """
        # Get Joke-ID from the file to use in logging
        joke_id = 'unknown'
        try:
            headers, _ = parse_joke_file(filepath)
            joke_id = headers.get('Joke-ID', 'unknown')
        except Exception as e:
            self.logger.error(f"{joke_id} Could not parse headers from {filepath}: {e}")

        self.logger.debug(f"{joke_id} Starting to process file {filepath}")

        # Move file to tmp/ directory to prevent concurrent processing
        input_dir = os.path.dirname(filepath)
        tmp_dir = os.path.join(input_dir, 'tmp')
        os.makedirs(tmp_dir, exist_ok=True)

        filename = os.path.basename(filepath)
        tmp_filepath = os.path.join(tmp_dir, filename)

        try:
            shutil.move(filepath, tmp_filepath)
            self.logger.debug(f"{joke_id} Moved file to tmp for processing: {tmp_filepath}")
            filepath = tmp_filepath  # Update filepath to tmp location
        except Exception as e:
            self.logger.error(f"{joke_id} Failed to move file to tmp directory: {e}")
            # If we can't move to tmp, we can't safely process this file
            return

        # Write joke ID to PROCESSING status file
        processing_file = os.path.join(tmp_dir, 'PROCESSING')
        try:
            with open(processing_file, 'w', encoding='utf-8') as f:
                f.write(joke_id)
            self.logger.debug(f"{joke_id} Wrote processing status")
        except Exception as e:
            self.logger.warning(f"{joke_id} Failed to write PROCESSING file: {e}")
            # Continue processing even if we can't write the status file

        retries = 0
        max_retries = self.config.MAX_RETRIES

        try:
            while retries <= max_retries:
                try:
                    # Read the file
                    headers, content = parse_joke_file(filepath)

                    # Call the abstract process function
                    success, updated_headers, updated_content, reject_reason = self.process_file(filepath, headers, content)

                    if success:
                        self._move_to_output(filepath, updated_headers, updated_content)
                        self.logger.debug(f"{joke_id} Successfully processed file {filepath}")
                        return
                    else:
                        # If not successful, check if we've exhausted retries
                        if retries < max_retries:
                            retries += 1
                            self.logger.warning(f"{joke_id} Processing failed for {filepath}, retry {retries}/{max_retries}")
                        else:
                            # Final failure - move to reject directory
                            self._move_to_reject(filepath, headers, content, reject_reason)
                            self.logger.error(f"{joke_id} Processing failed after {max_retries} retries for {filepath}. Reason: {reject_reason}")
                            return

                except Exception as e:
                    # If exception occurs, check if we can retry
                    if retries < max_retries:
                        retries += 1
                        self.logger.warning(f"{joke_id} Exception in processing {filepath}, retry {retries}/{max_retries}: {e}")
                    else:
                        # Final failure - move to reject directory
                        # If headers is not defined at this point (due to exception during parse), we still need to handle this
                        try:
                            headers, content = parse_joke_file(filepath)
                        except:
                            # At this point, we don't have working headers so we make placeholders
                            headers = {}
                            content = ""
                        self._move_to_reject(filepath, headers, content, f"Exception occurred: {e}")
                        self.logger.error(f"{joke_id} Exception in processing {filepath} after {max_retries} retries: {e}")
                        return
        finally:
            # Always delete PROCESSING file when done
            if os.path.exists(processing_file):
                try:
                    os.remove(processing_file)
                    self.logger.debug(f"{joke_id} Deleted processing status")
                except Exception as e:
                    self.logger.warning(f"{joke_id} Failed to delete PROCESSING file: {e}")
        
    def _move_to_output(self, filepath: str, headers: Dict[str, str], content: str):
        """
        Move a successful file to the output stage directory.
        
        Args:
            filepath: Path to the input file
            headers: Updated headers for the file
            content: Updated content for the file
        """
        # Update the Pipeline-Stage header
        headers['Pipeline-Stage'] = self.output_stage
        
        # Get Joke-ID from headers for logging
        joke_id = headers.get('Joke-ID', 'unknown')
        
        # Determine output directory based on where the file currently is
        # Files should stay in the same pipeline (main or priority)
        if self.config.PIPELINE_PRIORITY in filepath:
            final_output_dir = os.path.join(self.config.PIPELINE_PRIORITY, self.output_stage)
        else:
            final_output_dir = os.path.join(self.config.PIPELINE_MAIN, self.output_stage)

        # Write file atomically to output directory
        atomic_write(filepath, headers, content)
            
        atomic_move(filepath, final_output_dir)
        
        self.logger.debug(f"{joke_id} Moved successful file from {filepath} to {final_output_dir}")
    
    def _move_to_reject(self, filepath: str, headers: Dict[str, str], content: str, reason: str):
        """
        Move a failed file to the reject stage directory.
        
        Args:
            filepath: Path to the input file
            headers: Headers for the file (may be modified)
            content: Content for the file
            reason: Reason for rejection
        """
        # Update the Pipeline-Stage header
        headers['Pipeline-Stage'] = self.reject_stage
        
        # Add the Rejection-Reason to headers
        headers['Rejection-Reason'] = reason
        
        # Get Joke-ID from headers for logging
        joke_id = headers.get('Joke-ID', 'unknown')
        
        # Determine reject directory based on where the file currently is
        # Files should stay in the same pipeline (main or priority)
        if self.config.PIPELINE_PRIORITY in filepath:
            final_reject_dir = os.path.join(self.config.PIPELINE_PRIORITY, self.reject_stage)
        else:
            final_reject_dir = os.path.join(self.config.PIPELINE_MAIN, self.reject_stage)

        # Write file atomically to reject directory
        atomic_write(filepath, headers, content)
            
        atomic_move(filepath, final_reject_dir)

        # Log rejection to failure log file
        self._log_rejection(filepath, joke_id, reason)

        self.logger.debug(f"{joke_id} Moved rejected file from {filepath} to {final_reject_dir}. Reason: {reason}")

    def _log_rejection(self, filepath: str, joke_id: str, reason: str):
        """
        Log rejection to the appropriate failure log file.

        Args:
            filepath: Path to the file being rejected
            joke_id: Joke ID
            reason: Rejection reason
        """
        # Determine pipeline (main or pri)
        if self.config.PIPELINE_PRIORITY in filepath:
            pipeline = 'pri'
        else:
            pipeline = 'main'

        # Determine reject stage name from self.reject_stage
        # Extract just the stage name (e.g., "duplicate" from "51_rejected_duplicate")
        stage_name = self.reject_stage.split('_', 1)[1] if '_' in self.reject_stage else self.reject_stage

        # Build log filename: logs/main_reject_duplicate.log
        log_filename = f"{pipeline}_{stage_name}.log"
        log_filepath = os.path.join(self.config.LOG_DIR, log_filename)

        # Replace newlines in reason with spaces
        clean_reason = reason.replace('\n', ' ').replace('\r', ' ')

        # Write log entry: <joke_id> <reason>
        try:
            os.makedirs(self.config.LOG_DIR, exist_ok=True)
            with open(log_filepath, 'a', encoding='utf-8') as f:
                f.write(f"{joke_id} {clean_reason}\n")
            self.logger.debug(f"{joke_id} Logged rejection to {log_filepath}")
        except Exception as e:
            self.logger.warning(f"{joke_id} Failed to write rejection log: {e}")