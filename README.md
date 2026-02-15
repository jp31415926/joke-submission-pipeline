# joke-submission-pipeline

This pipeline processes joke submissions from emails through multiple stages, ensuring high-quality joke handling through automated processing and manual review.

## Architecture

The pipeline follows a batch-oriented, file-based state machine approach with independent processing stages. Each joke submission goes through 8 processing stages before reaching the ready-for-review state:

1. **Incoming** - Initial email parsing with joke-extractor
2. **Parsed** - Email structure parsing
3. **Deduped** - Duplicate checking with TF-IDF
4. **Clean Checked** - Cleanliness verification using LLM
5. **Formatted** - Grammar and punctuation formatting using LLM
6. **Categorized** - Category assignment using LLM
7. **Titled** - Title assignment (if needed)
8. **Ready for Review** - Final review stage

## Implementation

- Uses Python 3.x with Ollama for LLM integration
- Atomic file operations implemented through file_utils.py
- Configurable through config.py
- Processes 1 joke file per stage execution
- Low volume expected (1-10 jokes per day)

## Pipeline Stages

Each stage processes files in directories under `pipeline-main/` and `pipeline-priority/`. All stages use tmp/ subdirectories for atomic file operations to prevent partial file writes.

### Stage Directories

Each directory includes:
- `tmp/` - For atomic operations
- Standard queue processing structure

### File Format

- Each joke is a single text file named with UUID
- Header format: Joke-ID, Title, Submitter, etc. 
- Content after blank line separator

## Requirements

- Local LLM (Ollama with llama3 model)
- Unix/Linux machine
- Python 3.x

## Testing

Run tests with `python3 -m pytest tests/`