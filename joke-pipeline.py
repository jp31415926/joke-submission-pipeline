#!/usr/bin/env python3
"""
Main pipeline orchestration script for joke submission pipeline.

This script runs all stages in sequence to process jokes from email
extraction through to ready-for-review state.
"""

import sys
import argparse
from typing import Optional

import config
from logging_utils import setup_logging, get_logger
from stage_incoming import IncomingProcessor
from stage_parsed import ParsedProcessor
from stage_deduped import DedupedProcessor
from stage_clean_checked import CleanCheckedProcessor
from stage_formatted import FormattedProcessor
from stage_categorized import CategorizedProcessor


def run_pipeline(pipeline_type: str = "both", stage_only: Optional[str] = None):
  """
  Run the joke pipeline.

  Args:
    pipeline_type: Which pipeline to run - "main", "priority", or "both"
    stage_only: If specified, run only this stage (e.g., "parsed", "deduped")
  """
  logger = get_logger("Pipeline")

  logger.info("=" * 70)
  logger.info(f"Starting joke pipeline (type: {pipeline_type})")
  if stage_only:
    logger.info(f"Running single stage only: {stage_only}")
  logger.info("=" * 70)

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
      logger.info("-" * 70)
      logger.info(f"Running stage: {stage_name}")
      logger.info("-" * 70)

      processor = processor_class()
      processor.run()

      logger.info(f"Completed stage: {stage_name}")

    logger.info("=" * 70)
    logger.info("Pipeline execution completed successfully")
    logger.info("=" * 70)
    return True

  except Exception as e:
    logger.error("=" * 70)
    logger.error(f"Pipeline execution failed: {e}")
    logger.error("=" * 70)
    return False


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

  args = parser.parse_args()

  # Setup logging
  if args.verbose:
    log_level = 'DEBUG'
  elif args.log_level:
    log_level = args.log_level
  else:
    log_level = config.LOG_LEVEL

  setup_logging(config.LOG_DIR, log_level, log_to_stdout=args.log_to_stdout)

  logger = get_logger("Main")
  logger.info(f"Joke Pipeline starting with arguments: {vars(args)}")

  # Run pipeline
  success = run_pipeline(
    pipeline_type=args.pipeline,
    stage_only=args.stage
  )

  # Exit with appropriate code
  if success:
    logger.info("Pipeline completed successfully")
    sys.exit(0)
  else:
    logger.error("Pipeline failed")
    sys.exit(1)


if __name__ == '__main__':
  main()
