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
from typing import Optional, Tuple

import config
from logging_utils import setup_logging, get_logger
from ollama_server_pool import initialize_server_pool, get_server_pool
from stage_incoming import IncomingProcessor
from stage_parsed import ParsedProcessor
from stage_deduped import DedupedProcessor
from stage_clean_checked import CleanCheckedProcessor
from stage_formatted import FormattedProcessor
from stage_categorized import CategorizedProcessor


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
    # Check if this is incoming or rejected_parse (both contain .eml files)
    # Otherwise look for .txt files
    is_email_stage = (directory_path.endswith('01_incoming') or
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

  # Collect status for all directories
  status_data = []
  total_main = 0
  total_priority = 0
  overall_oldest = None
  overall_oldest_info = None

  for dir_name in sorted_dirs:
    main_dir = os.path.join(config.PIPELINE_MAIN, dir_name)
    priority_dir = os.path.join(config.PIPELINE_PRIORITY, dir_name)

    main_count, main_oldest = get_directory_status(main_dir)
    priority_count, priority_oldest = get_directory_status(priority_dir)

    total_main += main_count
    total_priority += priority_count

    # Determine which pipeline has the oldest file
    oldest_age = None
    oldest_pipeline = None
    if main_oldest and priority_oldest:
      if main_oldest < priority_oldest:
        oldest_age = main_oldest
        oldest_pipeline = "M"
      else:
        oldest_age = priority_oldest
        oldest_pipeline = "P"
    elif main_oldest:
      oldest_age = main_oldest
      oldest_pipeline = "M"
    elif priority_oldest:
      oldest_age = priority_oldest
      oldest_pipeline = "P"

    # Track overall oldest
    if oldest_age:
      if overall_oldest is None or oldest_age < overall_oldest:
        overall_oldest = oldest_age
        overall_oldest_info = (dir_name, oldest_pipeline)

    status_data.append({
      'dir': dir_name,
      'main_count': main_count,
      'priority_count': priority_count,
      'oldest_age': oldest_age,
      'oldest_pipeline': oldest_pipeline
    })

  # Check tmp directories for in-progress files
  main_tmp = 0
  priority_tmp = 0
  for stage_dir in config.STAGES.values():
    main_tmp_dir = os.path.join(config.PIPELINE_MAIN, stage_dir, 'tmp')
    priority_tmp_dir = os.path.join(config.PIPELINE_PRIORITY, stage_dir, 'tmp')

    try:
      if os.path.exists(main_tmp_dir):
        main_tmp += len([f for f in os.listdir(main_tmp_dir)
                         if f.endswith('.txt')])
    except (FileNotFoundError, OSError, PermissionError):
      # Directory was moved/deleted or is inaccessible
      pass

    try:
      if os.path.exists(priority_tmp_dir):
        priority_tmp += len([f for f in os.listdir(priority_tmp_dir)
                             if f.endswith('.txt')])
    except (FileNotFoundError, OSError, PermissionError):
      # Directory was moved/deleted or is inaccessible
      pass

  # Print status
  print("Joke Pipeline Status")
  print("=" * 80)
  print(f"{'Stage':<28} {'Main':>6} {'Prior':>6}  {'Oldest':<15}")
  print("-" * 80)

  for item in status_data:
    if item['oldest_age']:
      oldest_str = f"{format_age(item['oldest_age'])} ({item['oldest_pipeline']})"
    else:
      oldest_str = "-"

    print(f"{item['dir']:<28} {item['main_count']:>6} "
          f"{item['priority_count']:>6}  {oldest_str:<15}")

  print("-" * 80)
  print(f"{'Totals:':<28} {total_main:>6} {total_priority:>6}")
  print()
  print(f"In Progress (tmp/):  Main: {main_tmp}  Priority: {priority_tmp}")
  print()

  total_files = total_main + total_priority
  if overall_oldest:
    oldest_label = overall_oldest_info[0]
    oldest_pipe = "Main" if overall_oldest_info[1] == "M" else "Priority"
    print(f"Overall: {total_files} files total")
    print(f"Oldest file: {format_age(overall_oldest)} "
          f"in {oldest_label}/{oldest_pipe}")
  else:
    print(f"Overall: {total_files} files total")


def run_pipeline(pipeline_type: str = "both", stage_only: Optional[str] = None):
  """
  Run the joke pipeline.

  Args:
    pipeline_type: Which pipeline to run - "main", "priority", or "both"
    stage_only: If specified, run only this stage (e.g., "parsed", "deduped")
  """
  logger = get_logger("Pipeline")

  #logger.info("=" * 70)
  logger.info(f"Starting joke pipeline (type: {pipeline_type})")
  if stage_only:
    logger.info(f"Running single stage only: {stage_only}")
  #logger.info("=" * 70)

  # Define all stages in order
  all_stages = {
    "incoming": IncomingProcessor,
    "parsed": ParsedProcessor,
    "deduped": DedupedProcessor,
    "clean_checked": CleanCheckedProcessor,
    "formatted": FormattedProcessor,
    "categorized": CategorizedProcessor
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
      #logger.info("-" * 70)
      logger.info(f"Running stage: {stage_name}")
      #logger.info("-" * 70)

      processor = processor_class()
      processor.run()

      logger.info(f"Completed stage: {stage_name}")

    #logger.info("=" * 70)
    logger.info("Pipeline execution completed successfully")
    #logger.info("=" * 70)
    return True

  except Exception as e:
    #logger.error("=" * 70)
    logger.error(f"Pipeline execution failed: {e}")
    #logger.error("=" * 70)
    return False


def signal_handler(signum, frame):
  """Handle signals by cleaning up locks."""
  logger = get_logger("SignalHandler")
  logger.info(f"Received signal {signum}, cleaning up locks...")

  server_pool = get_server_pool()
  if server_pool:
    server_pool.cleanup_all_locks()

  logger.info("Cleanup complete, exiting")
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
  %(prog)s --stage parsed

  # Run with verbose logging
  %(prog)s --verbose

  # Run with custom log level
  %(prog)s --log-level WARNING

  # Run with logging to stdout
  %(prog)s --log-to-stdout

Stages (in order):
  incoming      - Extract jokes from emails
  parsed        - Check for duplicates using TF-IDF
  deduped       - Check cleanliness using LLM
  clean_checked - Format jokes using LLM
  formatted     - Categorize jokes using LLM
  categorized   - Generate titles and final validation
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
      'incoming',
      'parsed',
      'deduped',
      'clean_checked',
      'formatted',
      'categorized'
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

  args = parser.parse_args()

  # Handle --status flag (no logging needed)
  if args.status:
    show_status()
    sys.exit(0)

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

  # Check for and remove ALL_STOP file if it exists
  if os.path.exists(config.ALL_STOP):
    logger.info(f"Removing ALL_STOP file at {config.ALL_STOP}")
    try:
      os.remove(config.ALL_STOP)
      logger.info("ALL_STOP file removed successfully")
    except Exception as e:
      logger.warning(f"Failed to remove ALL_STOP file: {e}")

  # Initialize Ollama server pool
  logger.info("Initializing Ollama server pool...")
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
    #logger.info("Pipeline completed successfully")
    sys.exit(0)
  else:
    logger.error("Pipeline failed")
    sys.exit(1)


if __name__ == '__main__':
  main()
