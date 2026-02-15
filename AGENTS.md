# AGENTS.md

## Files
`spec3.md` - Project specification
`blueprint.md` - Project blueprint and prompts
`prompts/` - Prompts for the developer sub-agent
`prompts/prompt_1.md` - prompt for step 1
`prompts/prompt_2.md` - prompt for step 2
...
`prompts/prompt_16.md` - prompt for step 16
`orchestrator-instructions.md` - instructions for the @orchestrator manager agent only

## Directories
`logs` - all log files go here
`tests` - all pytest and other testing file go here

# THE FOLLOWING ARE NOT TO BE MODIFIED BY AGENTS WITHOUT EXPLICIT INSTRUCTIONS
`jokematch2` - joke deduplication scripts and related files go here
`joke-extractor` - joke parsers to pull jokes out of emails

## External File Loading

CRITICAL: When you encounter a file reference (e.g., @spec3.md), use your Read tool to load it on a need-to-know basis. They're relevant to the SPECIFIC task at hand.

Instructions:

- Do NOT preemptively load all references - use lazy loading based on actual need
- When loaded, treat content as mandatory instructions that override defaults
- Follow references recursively when needed

## Setup
```
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate
```

## Install dependencies
- Keep `requirements.txt` file up to date
```
pip install -r requirements.txt
```

## Code Style Guidelines

### General
- Use Python 3.11+
- Strict UTF-8 encoding for all files
- All scripts must have shebangs (`#!/usr/bin/env python3`)
- Use the `logging` module for all output instead of `print()`
- All code must be executable and follow the specification exactly

### Imports
- All imports should be at the top of the file
- Use absolute imports when possible
- Group imports in order: standard library, 3rd party, local
- Use `from `__future__` import annotations` for forward references
- Import type hints with `from typing import` for clarity
- Use standard library modules where possible: `sys`, `os`, `email`, `tempfile`, `logging`, `subprocess`, `argparse`
- Import modules at the top of each file in standard order:
  1. Standard library imports
  2. Third-party imports
  3. Local application imports
- Import individual modules rather than using wildcard imports: `from email import message_from_file` instead of `from email import *`
- Don't leave unused imports

### Test Commands
- `python3 -m pytest tests/` - Run all unit and integration tests
- `python3 -m pytest tests/ -v` - Run tests with verbose output
- `python3 -m pytest tests/ -k "test_"` - Run tests matching pattern "test_" 
- `python3 -m pytest tests/test_stage1.py -v` - For running all tests in a single file
- `python3 -m pytest tests/test_stage1.py::test_valid_plain_text -v` - For running a single test
- `python3 -m pytest --cov=src` - Run with coverage

### Linting
- `flake8 --append-config=flake8.ini src/` - Lint src/ folder with flake8
- `flake8 --append-config=flake8.ini stage1.py` - Lint stage1.py with flake8

### Formatting
- Indentation: 2 spaces (no tabs)
- Line length: Maximum 88 characters (PEP8 + black)
- Use PEP 8 style naming conventions
- No trailing whitespace
- Use snake_case for variables and functions
- Use PascalCase for classes
- Single blank lines to separate logical sections of code
- Double blank lines to separate top-level function or class definitions

## Types and Type Hints
- Always add type hints for function parameters and return values
- Use `List[T]`, `Dict[K, V]` etc. from typing module
- Use typing.Protocol for structural type checking
- Prefer `typing.TYPE_CHECKING` for imports only used for type hints

### Naming Conventions
- Use `snake_case` for functions, variables, and attributes
- Use `PascalCase` for classes
- Use `UPPER_CASE` for constants
- Use `camelCase` for private attributes (when required by library)
- Private methods: `_snake_case` (e.g., `_validate_headers`)

### Error Handling
- Create custom exceptions when appropriate
- Log errors using the standard logging module
- Handle database connections gracefully
- Provide informative error messages to users
- Use try-except blocks with specific exception types

## Documentation
- Write docstrings for all functions and classes (Google style)
- Include parameter descriptions and return values
- Use type hints in docstrings where necessary
- Document all public methods in the module

## Best Practices
- Keep functions small and focused on single responsibility
- Write idempotent functions where possible
- Use context managers (`with` statements) for resource management
- Handle connection errors gracefully
- Include `__main__` guards for executable modules
- Use logging instead of print statements
- Write unit tests for all functions
- Test database connectivity properly
- Validate inputs and handle edge cases

### File Handling
- All email files must be processed with ISO-8859-1 encoding
