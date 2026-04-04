#!/usr/bin/env python3
"""
Main pipeline orchestration script for joke submission pipeline.

This script runs all stages in sequence to process jokes from email
extraction through to ready-for-review state.
"""

import sys
import signal
import argparse
import os
import time
from typing import Optional, Tuple, List

import config
from logging_utils import setup_logging, get_logger
from file_utils import parse_joke_file, atomic_write
from ollama_server_pool import initialize_server_pool, get_server_pool
from stage_parse import ParseProcessor
from stage_dedup import DedupProcessor
from stage_clean_check import CleanCheckProcessor
from stage_format import FormatProcessor
from stage_categorize import CategorizeProcessor
from stage_title import TitleProcessor


def get_directory_status(directory_path: str) -> Tuple[int, Optional[float]]:
  """
  Get file count and oldest file timestamp for a directory.

  Args:
    directory_path: Path to directory to analyze

  Returns:
    Tuple of (file_count, oldest_timestamp)
  """
  if not os.path.exists(directory_path):
    return 0, None

  try:
    # Check if this is parse or rejected_parse (both contain .eml files)
    # Otherwise look for .txt files
    is_email_stage = (directory_path.endswith('01_parse') or
                      directory_path.endswith('50_rejected_parse'))

    if is_email_stage:
      files = [f for f in os.listdir(directory_path)
               if f.endswith('.eml') and not f.startswith('.')]
    else:
      files = [f for f in os.listdir(directory_path)
               if f.endswith('.txt') and not f.startswith('.')]

    count = len(files)

    oldest_time = None
    if files:
      # Find oldest file, handling cases where files may be moved/deleted
      # during execution
      for candidate_file in sorted(files):
        try:
          file_path = os.path.join(directory_path, candidate_file)
          mtime = os.path.getmtime(file_path)
          if oldest_time is None or mtime < oldest_time:
            oldest_time = mtime
        except (FileNotFoundError, OSError):
          # File was moved or deleted, skip it
          count -= 1
          continue

    return count, oldest_time

  except (FileNotFoundError, OSError, PermissionError):
    # Directory was moved/deleted or is inaccessible
    return 0, None


def format_age(timestamp: Optional[float]) -> str:
  """
  Format timestamp as relative age.

  Args:
    timestamp: Unix timestamp or None

  Returns:
    Formatted age string (e.g., "5m ago", "3h ago", "2d ago")
  """
  if timestamp is None:
    return "-"

  age_seconds = time.time() - timestamp
  if age_seconds < 3600:
    minutes = int(age_seconds / 60)
    return f"{minutes}m ago" if minutes > 0 else "just now"
  elif age_seconds < 86400:
    hours = int(age_seconds / 3600)
    return f"{hours}h ago"
  else:
    days = int(age_seconds / 86400)
    return f"{days}d ago"


def format_joke_id(joke_id: Optional[str]) -> str:
  """
  Format joke ID as first5...last5.

  Args:
    joke_id: Joke ID string or None

  Returns:
    Formatted joke ID (e.g., "abc12...def89") or empty string
  """
  if not joke_id or len(joke_id) == 0:
    return ""

  if len(joke_id) <= 13:  # If short enough, just return it
    return joke_id

  return f"{joke_id[:5]}...{joke_id[-5:]}"


def get_processing_id(directory_path: str) -> Optional[str]:
  """
  Read the joke ID from the PROCESSING file in tmp/ subdirectory.

  Args:
    directory_path: Path to the stage directory

  Returns:
    Joke ID being processed or None
  """
  processing_file = os.path.join(directory_path, 'tmp', 'PROCESSING')
  try:
    if os.path.exists(processing_file):
      with open(processing_file, 'r', encoding='utf-8') as f:
        return f.read().strip()
  except (FileNotFoundError, OSError, PermissionError):
    pass
  return None


def show_status() -> None:
  """Display pipeline status information."""
  # Collect all stage and reject directories
  all_dirs = {}
  for stage_name, stage_dir in config.STAGES.items():
    all_dirs[stage_dir] = stage_dir
  for reject_name, reject_dir in config.REJECTS.items():
    all_dirs[reject_dir] = reject_dir

  # Sort alphabetically by directory name
  sorted_dirs = sorted(all_dirs.keys())

  # Calculate max stage name length for column width
  max_name_len = max(len(dir_name) for dir_name in sorted_dirs)
  name_col_width = max_name_len + 2

  # Collect status for both pipelines
  main_status_data = []
  priority_status_data = []
  total_main = 0
  total_priority = 0

  for dir_name in sorted_dirs:
    main_dir = os.path.join(config.PIPELINE_MAIN, dir_name)
    priority_dir = os.path.join(config.PIPELINE_PRIORITY, dir_name)

    main_count, main_oldest = get_directory_status(main_dir)
    priority_count, priority_oldest = get_directory_status(priority_dir)
    main_processing = get_processing_id(main_dir)
    priority_processing = get_processing_id(priority_dir)

    total_main += main_count
    total_priority += priority_count

    main_status_data.append({
      'dir': dir_name,
      'count': main_count,
      'oldest': main_oldest,
      'processing': main_processing
    })

    priority_status_data.append({
      'dir': dir_name,
      'count': priority_count,
      'oldest': priority_oldest,
      'processing': priority_processing
    })

  # Print header
  print("Joke Pipeline Status")
  print("=" * 80)
  print()

  # Print Main Pipeline
  print("Main Pipeline:")
  header = f"{'Stage':<{name_col_width}}  {'Count':>5}  {'Processing':<18}  {'Oldest':<15}"
  print(header)
  print("-" * len(header))

  for item in main_status_data:
    count_str = f"{item['count']:>5}"
    processing_str = f"{format_joke_id(item['processing']):<18}"
    oldest_str = f"{format_age(item['oldest']):<15}"
    print(f"{item['dir']:<{name_col_width}}  {count_str}  {processing_str}  {oldest_str}")

  print("-" * len(header))
  print(f"{'Total:':<{name_col_width}}  {total_main:>5}")
  print()

  # Print Priority Pipeline
  print("Priority Pipeline:")
  print(header)
  print("-" * len(header))

  for item in priority_status_data:
    count_str = f"{item['count']:>5}"
    processing_str = f"{format_joke_id(item['processing']):<18}"
    oldest_str = f"{format_age(item['oldest']):<15}"
    print(f"{item['dir']:<{name_col_width}}  {count_str}  {processing_str}  {oldest_str}")

  print("-" * len(header))
  print(f"{'Total:':<{name_col_width}}  {total_priority:>5}")
  print()

  # Print overall summary
  total_files = total_main + total_priority
  print(f"Overall: {total_files} files total ({total_main} main, {total_priority} priority)")


def run_pipeline(pipeline_type: str = "both", stage_only: Optional[str] = None):
  """
  Run the joke pipeline.

  Args:
    pipeline_type: Which pipeline to run - "main", "priority", or "both"
    stage_only: If specified, run only this stage (e.g., "parsed", "deduped")
  """
  logger = get_logger("Pipeline")

  logger.debug(f"Starting joke pipeline (type: {pipeline_type})")
  if stage_only:
    logger.debug(f"Running single stage only: {stage_only}")

  # Define all stages in order
  all_stages = {
    "parse": ParseProcessor,
    "dedup": DedupProcessor,
    "clean_check": CleanCheckProcessor,
    "format": FormatProcessor,
    "categorize": CategorizeProcessor,
    "title": TitleProcessor,
  }

  # Determine which stages to run
  if stage_only:
    if stage_only not in all_stages:
      logger.error(f"Invalid stage: {stage_only}")
      logger.error(f"Valid stages: {', '.join(all_stages.keys())}")
      return False
    stages_to_run = {stage_only: all_stages[stage_only]}
  else:
    stages_to_run = all_stages

  # Run each stage in order
  try:
    for stage_name, processor_class in stages_to_run.items():
      logger.debug(f"Running stage: {stage_name}")

      processor = processor_class()
      processor.run()

      logger.debug(f"Completed stage: {stage_name}")

    logger.debug("Pipeline execution completed successfully")
    return True

  except Exception as e:
    logger.error(f"Pipeline execution failed: {e}")
    return False


# Maps reject stage key -> stage the joke should re-enter for reprocessing
RETRY_STAGE_MAP = {
  'dedup': config.STAGES['dedup'],
  'clean_check': config.STAGES['clean_check'],
  'format': config.STAGES['format'],
  'categorize': config.STAGES['categorize'],
  'title': config.STAGES['title'],
}


def retry_jokes(
  pipeline: str,
  stage: str,
  joke_ids: List[str]
) -> bool:
  """
  Move rejected jokes back to the appropriate stage for reprocessing.

  Finds each joke by ID in the reject directory, clears the
  Rejection-Reason header, updates Pipeline-Stage, and moves the file
  to the retry stage directory.

  Args:
    pipeline: 'main' or 'priority'
    stage: Reject stage key (e.g. 'duplicate', 'cleanliness')
    joke_ids: List of joke ID strings to retry

  Returns:
    True if all IDs were found and moved; False if any were not found.
  """
  logger = get_logger("retry")

  pipeline_dir = (
    config.PIPELINE_MAIN if pipeline == 'main' else config.PIPELINE_PRIORITY
  )
  reject_dir = os.path.join(pipeline_dir, config.REJECTS[stage])
  retry_stage = RETRY_STAGE_MAP[stage]
  retry_dir = os.path.join(pipeline_dir, retry_stage)

  os.makedirs(retry_dir, exist_ok=True)
  os.makedirs(os.path.join(retry_dir, 'tmp'), exist_ok=True)

  all_found = True
  for joke_id in joke_ids:
    source_path = os.path.join(reject_dir, f"{joke_id}.txt")
    if not os.path.exists(source_path):
      logger.error(f"{joke_id} Not found in {reject_dir}")
      print(f"ERROR: {joke_id} not found in {reject_dir}", file=sys.stderr)
      all_found = False
      continue

    try:
      headers, content = parse_joke_file(source_path)

      # Clear rejection metadata and set new stage
      headers.pop('Rejection-Reason', None)
      headers['Pipeline-Stage'] = retry_stage

      # Write to retry dir atomically, then remove source
      dest_path = os.path.join(retry_dir, f"{joke_id}.txt")
      atomic_write(dest_path, headers, content)
      os.remove(source_path)

      logger.info(
        f"{joke_id} Moved from {config.REJECTS[stage]} to {retry_stage}"
      )
      print(f"OK: {joke_id} -> {retry_stage}")

    except Exception as e:
      logger.error(f"{joke_id} Failed to retry: {e}")
      print(f"ERROR: {joke_id} failed: {e}", file=sys.stderr)
      all_found = False

  return all_found


def signal_handler(signum, frame):
  """Handle signals by cleaning up locks."""
  logger = get_logger("SignalHandler")
  logger.info(f"Received signal {signum}, cleaning up locks")

  server_pool = get_server_pool()
  if server_pool:
    server_pool.cleanup_all_locks()

  logger.debug("Cleanup complete, exiting")
  sys.exit(1)


def main():
  """Main entry point with command-line argument parsing."""
  parser = argparse.ArgumentParser(
    description="Joke submission pipeline - processes jokes from emails to ready-for-review",
    formatter_class=argparse.RawDescriptionHelpFormatter,
    epilog="""
Examples:
  # Run full pipeline on both main and priority
  %(prog)s

  # Run only main pipeline
  %(prog)s --pipeline main

  # Run only priority pipeline
  %(prog)s --pipeline priority

  # Run specific stage only
  %(prog)s --stage dedup

  # Run with verbose logging
  %(prog)s --verbose

  # Run with custom log level
  %(prog)s --log-level WARNING

  # Run with logging to stdout
  %(prog)s --log-to-stdout

  # Retry rejected jokes
  %(prog)s --retry main dedup <id1> <id2>

Stages (in order):
  parse       - Extract jokes from emails
  dedup       - Check for duplicates using TF-IDF
  clean_check - Check cleanliness using LLM
  format      - Format jokes using LLM
  categorize  - Categorize jokes using LLM
  title       - Generate titles and final validation

Retry stages (reject stage -> re-enters at):
  dedup       -> 02_dedup
  clean_check -> 03_clean_check
  format      -> 04_format
  categorize  -> 05_categorize
  title       -> 06_title
    """
  )

  parser.add_argument(
    '--pipeline',
    choices=['main', 'priority', 'both'],
    default='both',
    help='Which pipeline to run (default: both)'
  )

  parser.add_argument(
    '--stage',
    choices=[
      'parse',
      'dedup',
      'clean_check',
      'format',
      'categorize',
      'title',
    ],
    help='Run specific stage only (optional)'
  )

  parser.add_argument(
    '--log-level',
    choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
    default=None,
    help='Set logging level (default: INFO from config)'
  )

  parser.add_argument(
    '--log-to-stdout',
    action='store_true',
    help='Also log to stdout (default: log to file only)'
  )

  parser.add_argument(
    '--verbose',
    action='store_true',
    help='Enable DEBUG level logging (shorthand for --log-level DEBUG)'
  )

  parser.add_argument(
    '--status',
    action='store_true',
    help='Show pipeline status and exit (file counts, oldest files, etc.)'
  )

  parser.add_argument(
    '--retry',
    nargs=argparse.REMAINDER,
    metavar='',
    help=(
      'Retry rejected jokes: --retry <pipeline> <stage> <id1> [id2 ...]\n'
      '  pipeline: main or priority\n'
      '  stage: ' + ', '.join(RETRY_STAGE_MAP.keys())
    )
  )

  args = parser.parse_args()

  # Handle --status flag (no logging needed)
  if args.status:
    show_status()
    sys.exit(0)

  # Handle --retry flag
  if args.retry is not None:
    retry_args = args.retry
    if len(retry_args) < 3:
      parser.error(
        '--retry requires: --retry <pipeline> <stage> <id1> [id2 ...]\n'
        '  pipeline: main or priority\n'
        '  stage: ' + ', '.join(RETRY_STAGE_MAP.keys())
      )

    pipeline = retry_args[0]
    stage = retry_args[1]
    joke_ids = retry_args[2:]

    if pipeline not in ('main', 'priority'):
      parser.error(
        f"--retry pipeline must be 'main' or 'priority', got: '{pipeline}'"
      )
    valid_stages = list(RETRY_STAGE_MAP.keys())
    if stage not in valid_stages:
      parser.error(
        f"--retry stage must be one of: {', '.join(valid_stages)}, got: '{stage}'"
      )

    success = retry_jokes(pipeline, stage, joke_ids)
    sys.exit(0 if success else 1)

  # Setup logging
  if args.verbose:
    log_level = 'DEBUG'
    log_to_stdout = True  # --verbose implies stdout logging
  elif args.log_level:
    log_level = args.log_level
    log_to_stdout = args.log_to_stdout
  else:
    log_level = config.LOG_LEVEL
    log_to_stdout = args.log_to_stdout

  setup_logging(config.LOG_DIR, log_level, log_to_stdout=log_to_stdout)

  logger = get_logger("Main")
  logger.debug(f"Joke Pipeline starting with arguments: {vars(args)}")

  # Initialize Ollama server pool
  logger.debug("Initializing Ollama server pool")
  initialize_server_pool(
    servers=config.OLLAMA_SERVERS,
    lock_dir=config.OLLAMA_LOCK_DIR,
    retry_wait=config.OLLAMA_LOCK_RETRY_WAIT,
    retry_max_attempts=config.OLLAMA_LOCK_RETRY_MAX_ATTEMPTS,
    retry_jitter=config.OLLAMA_LOCK_RETRY_JITTER
  )

  # Register signal handlers for cleanup
  signal.signal(signal.SIGINT, signal_handler)
  signal.signal(signal.SIGTERM, signal_handler)

  # Run pipeline
  success = run_pipeline(
    pipeline_type=args.pipeline,
    stage_only=args.stage
  )

  # Cleanup locks before exiting
  server_pool = get_server_pool()
  if server_pool:
    server_pool.cleanup_all_locks()

  # Exit with appropriate code
  if success:
    logger.debug("Pipeline completed successfully")
    sys.exit(0)
  else:
    logger.error("Pipeline failed")
    sys.exit(1)


if __name__ == '__main__':
  main()
