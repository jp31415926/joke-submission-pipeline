# Testing Guide

This document describes the testing infrastructure for the joke submission pipeline.

## Test Suite Overview

The project includes comprehensive tests covering:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test complete pipeline workflows end-to-end
- **Mock Tests**: Use mocked external dependencies for fast, reliable testing
- **Real Integration Tests**: Optional tests using real Ollama and external scripts

### Test Statistics
- **Total Tests**: 137+ unit and integration tests
- **Test Coverage**: Focus on critical paths, error handling, and edge cases
- **Test Execution Time**: ~6 seconds (with mocks)

## Running Tests

### Run All Tests
```bash
python3 -m pytest tests/
```

### Run with Verbose Output
```bash
python3 -m pytest tests/ -v
```

### Run Specific Test File
```bash
python3 -m pytest tests/test_file_utils.py
python3 -m pytest tests/test_stage_incoming.py
python3 -m pytest tests/test_integration.py
```

### Run Specific Test Function
```bash
python3 -m pytest tests/test_file_utils.py::test_parse_joke_file
python3 -m pytest tests/test_integration.py::test_full_pipeline_clean_jokes
```

### Run Tests Matching Pattern
```bash
# Run all tests with "duplicate" in the name
python3 -m pytest tests/ -k duplicate

# Run all integration tests
python3 -m pytest tests/test_integration.py -v
```

### Run with Coverage Report
```bash
# Generate coverage report
python3 -m pytest --cov=. --cov-report=html tests/

# View coverage report
open htmlcov/index.html
```

### Run Tests in Parallel (Faster)
```bash
# Install pytest-xdist first: pip install pytest-xdist
python3 -m pytest tests/ -n auto
```

## Test Organization

### Unit Tests
Located in `tests/test_*.py` files:

- **test_config.py**: Configuration validation
- **test_file_utils.py**: File parsing, writing, atomic operations
- **test_logging_utils.py**: Logging infrastructure
- **test_external_scripts.py**: External script execution
- **test_ollama_client.py**: LLM client functionality
- **test_stage_processor.py**: Base stage processor logic
- **test_stage_incoming.py**: Email extraction stage
- **test_stage_parsed.py**: Duplicate detection stage
- **test_stage_deduped.py**: Cleanliness check stage
- **test_stage_clean_checked.py**: Formatting stage
- **test_stage_formatted.py**: Categorization stage
- **test_stage_categorized.py**: Title generation and validation
- **test_setup_directories.py**: Directory creation

### Integration Tests
Located in `tests/test_integration.py` and `tests/test_joke_pipeline.py`:

- **test_joke_pipeline.py**: Pipeline orchestration tests (mocked)
- **test_integration.py**: Comprehensive end-to-end tests

### Test Fixtures
Located in `tests/fixtures/`:

- **emails/**: Sample email files for testing
- **jokes/**: Sample joke files at various stages
- **integration/**: Comprehensive test data for integration tests
- **mock_joke_extract.py**: Mock joke extractor script
- **mock_search_tfidf.py**: Mock TF-IDF search script
- **sample_*.txt**: Various sample joke files

## Test Data Management

### Creating Test Jokes
```python
from file_utils import write_joke_file

headers = {
    'Joke-ID': 'test-uuid-123',
    'Title': 'Test Joke',
    'Submitter': 'test@example.com',
    'Pipeline-Stage': '02_parsed'
}
content = "Why did the chicken cross the road?\nTo get to the other side!"

write_joke_file('path/to/file.txt', headers, content)
```

### Using Test Fixtures
```python
import pytest
import os

@pytest.fixture
def sample_joke_file(tmp_path):
    """Create a temporary joke file for testing."""
    joke_file = tmp_path / "test_joke.txt"
    headers = {'Joke-ID': 'test-123', 'Title': 'Test'}
    content = "Test joke content"
    write_joke_file(str(joke_file), headers, content)
    return str(joke_file)

def test_something(sample_joke_file):
    # Use the fixture
    headers, content = parse_joke_file(sample_joke_file)
    assert headers['Joke-ID'] == 'test-123'
```

## Mock vs Real Dependencies

### Mocked Tests (Default)
Most tests use mocked external dependencies for:
- **Speed**: Tests run in seconds
- **Reliability**: No network dependencies
- **Isolation**: Test specific functionality without external factors

Mocked dependencies:
- Ollama LLM API calls
- joke-extract.py script
- search_tfidf.py script

### Real Integration Tests (Optional)
To run tests with real dependencies:

1. **Start Ollama**:
   ```bash
   # Ensure Ollama is running with llama3 model
   ollama run llama3
   ```

2. **Verify External Scripts**:
   ```bash
   # Test joke-extractor
   python3 joke-extractor/joke-extract.py --help

   # Test jokematch2
   python3 jokematch2/search_tfidf.py --help
   ```

3. **Run Integration Tests**:
   ```bash
   # Set environment variable to use real dependencies
   export USE_REAL_OLLAMA=1
   python3 -m pytest tests/test_integration.py -v
   ```

## Adding New Tests

### 1. Create Test File
```python
#!/usr/bin/env python3
"""
Test cases for my_new_module.
"""

import sys
import os
import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import my_new_module

def test_basic_functionality():
    """Test basic functionality."""
    result = my_new_module.do_something()
    assert result == expected_value

def test_error_handling():
    """Test error handling."""
    with pytest.raises(ValueError):
        my_new_module.do_something_invalid()
```

### 2. Use Fixtures for Setup/Teardown
```python
@pytest.fixture
def setup_test_environment(tmp_path):
    """Setup test environment."""
    # Setup code
    test_dir = tmp_path / "test"
    test_dir.mkdir()

    yield test_dir

    # Teardown code (runs after test)
    # cleanup if needed
```

### 3. Test Best Practices
- **One concept per test**: Each test should verify one specific behavior
- **Descriptive names**: Use clear test names like `test_duplicate_detection_rejects_similar_jokes`
- **AAA Pattern**: Arrange (setup), Act (execute), Assert (verify)
- **Test edge cases**: Empty inputs, boundary values, error conditions
- **Use fixtures**: Avoid code duplication with pytest fixtures
- **Mock external dependencies**: Keep tests fast and isolated

### Example Test Structure
```python
def test_parse_joke_file_with_missing_headers(tmp_path):
    """Test parsing joke file with missing optional headers."""
    # Arrange
    joke_file = tmp_path / "joke.txt"
    joke_file.write_text("Title: Test\n\nJoke content")

    # Act
    headers, content = parse_joke_file(str(joke_file))

    # Assert
    assert headers['Title'] == 'Test'
    assert content == 'Joke content'
```

## Test Coverage Requirements

### Minimum Coverage Goals
- **Critical paths**: 100% coverage
- **Error handling**: All error paths tested
- **Overall coverage**: 80%+ recommended

### Generate Coverage Report
```bash
# Terminal report
python3 -m pytest --cov=. --cov-report=term-missing tests/

# HTML report (more detailed)
python3 -m pytest --cov=. --cov-report=html tests/
```

### View Coverage by File
```bash
python3 -m pytest --cov=. --cov-report=term tests/
```

## Continuous Integration

For CI/CD pipelines, use:

```bash
# Run tests with coverage and fail if coverage is below threshold
python3 -m pytest --cov=. --cov-fail-under=80 tests/
```

## Troubleshooting Tests

### Common Issues

#### "ModuleNotFoundError"
```bash
# Ensure you're in the project root directory
cd /path/to/joke-submission-pipeline

# Ensure virtual environment is activated
source .venv/bin/activate

# Ensure dependencies are installed
pip install -r requirements.txt
```

#### "Ollama Connection Error" (in real integration tests)
```bash
# Start Ollama
ollama serve

# In another terminal, load the model
ollama run llama3
```

#### Tests are Slow
```bash
# Use mocked tests (default)
python3 -m pytest tests/

# Run in parallel
pip install pytest-xdist
python3 -m pytest tests/ -n auto
```

#### Test Data Issues
```bash
# Clean up test artifacts
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type d -name ".pytest_cache" -exec rm -rf {} +
find . -type d -name "*.pyc" -delete
```

## Performance Testing

### Measure Test Execution Time
```bash
# Show slowest tests
python3 -m pytest tests/ --durations=10

# Profile specific test
python3 -m pytest tests/test_integration.py --durations=0
```

### Memory Profiling
```bash
# Install memory profiler
pip install pytest-memprof

# Run with memory profiling
python3 -m pytest tests/ --memprof
```

## Development Workflow

### Before Committing
```bash
# 1. Run all tests
python3 -m pytest tests/

# 2. Check coverage
python3 -m pytest --cov=. tests/

# 3. Lint code (if using flake8)
flake8 --append-config=flake8.ini *.py src/
```

### After Adding New Features
```bash
# 1. Write tests first (TDD)
# 2. Implement feature
# 3. Run specific test
python3 -m pytest tests/test_new_feature.py -v

# 4. Run all tests to ensure no regression
python3 -m pytest tests/
```

## Additional Resources

- **pytest documentation**: https://docs.pytest.org/
- **pytest fixtures**: https://docs.pytest.org/en/stable/fixture.html
- **pytest-cov**: https://pytest-cov.readthedocs.io/
- **Python unittest.mock**: https://docs.python.org/3/library/unittest.mock.html

## Test Maintenance

### Regular Tasks
- Keep test data up to date with schema changes
- Remove obsolete tests when features are removed
- Refactor tests when code structure changes
- Update mocks when external APIs change

### When Tests Fail
1. **Read the error message carefully**
2. **Check if code changes broke existing functionality**
3. **Verify test assumptions are still valid**
4. **Update tests if requirements changed**
5. **Fix bugs if tests revealed issues**
