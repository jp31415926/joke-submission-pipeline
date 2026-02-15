#!/usr/bin/env python3
"""Tests for external_scripts module."""

import os
import sys
import pytest
import subprocess
import tempfile

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from external_scripts import run_external_script, parse_tfidf_score


class TestRunExternalScript:
  """Tests for run_external_script function."""

  def test_simple_command_echo(self):
    """Test running simple echo command."""
    return_code, stdout, stderr = run_external_script(
      '/bin/echo',
      ['hello', 'world']
    )
    assert return_code == 0
    assert 'hello world' in stdout
    assert stderr == ''

  def test_return_code_capture(self):
    """Test capturing non-zero return codes."""
    return_code, stdout, stderr = run_external_script(
      '/bin/false',
      []
    )
    assert return_code == 1

  def test_stdout_capture(self):
    """Test stdout capture."""
    return_code, stdout, stderr = run_external_script(
      '/bin/echo',
      ['test output']
    )
    assert return_code == 0
    assert 'test output' in stdout

  def test_stderr_capture(self):
    """Test stderr capture."""
    # Use sh to redirect output to stderr
    return_code, stdout, stderr = run_external_script(
      '/bin/sh',
      ['-c', 'echo "error message" >&2']
    )
    assert 'error message' in stderr

  def test_timeout_handling(self):
    """Test timeout handling with sleep command."""
    with pytest.raises(subprocess.TimeoutExpired):
      run_external_script(
        '/bin/sleep',
        ['10'],
        timeout=1
      )

  def test_nonexistent_script(self):
    """Test error handling for nonexistent script."""
    with pytest.raises(FileNotFoundError):
      run_external_script(
        '/nonexistent/script.py',
        []
      )

  def test_non_executable_script(self):
    """Test error handling for non-executable script."""
    # Create a non-executable file
    with tempfile.NamedTemporaryFile(
      mode='w',
      delete=False,
      suffix='.py'
    ) as f:
      f.write('#!/usr/bin/env python3\nprint("test")\n')
      temp_path = f.name

    try:
      # File exists but is not executable
      os.chmod(temp_path, 0o644)
      with pytest.raises(PermissionError):
        run_external_script(temp_path, [])
    finally:
      os.unlink(temp_path)

  def test_mock_search_tfidf_script(self):
    """Test running mock search_tfidf.py script."""
    script_path = os.path.join(
      os.path.dirname(__file__),
      'fixtures',
      'mock_search_tfidf.py'
    )

    return_code, stdout, stderr = run_external_script(
      script_path,
      []
    )

    assert return_code == 0
    assert '42 1234 Test Joke Title' in stdout


class TestParseTfidfScore:
  """Tests for parse_tfidf_score function."""

  def test_valid_output(self):
    """Test parsing valid tfidf output."""
    output = "91 9278 A Meaningful New Year's Gesture"
    score = parse_tfidf_score(output)
    assert score == 91

  def test_valid_output_with_leading_whitespace(self):
    """Test parsing output with leading whitespace."""
    output = "  42 1234 Test Joke Title  "
    score = parse_tfidf_score(output)
    assert score == 42

  def test_valid_output_minimal(self):
    """Test parsing minimal valid output."""
    output = "75"
    score = parse_tfidf_score(output)
    assert score == 75

  def test_empty_output(self):
    """Test error handling for empty output."""
    with pytest.raises(ValueError, match="Empty output"):
      parse_tfidf_score("")

  def test_whitespace_only_output(self):
    """Test error handling for whitespace-only output."""
    with pytest.raises(ValueError, match="Empty output after stripping"):
      parse_tfidf_score("   \n  \t  ")

  def test_invalid_format_non_integer(self):
    """Test error handling for non-integer first token."""
    with pytest.raises(ValueError, match="Invalid output format"):
      parse_tfidf_score("abc 1234 Test")

  def test_invalid_format_no_score(self):
    """Test error handling for missing score."""
    with pytest.raises(ValueError, match="Invalid output format"):
      parse_tfidf_score("not a number")

  def test_score_at_boundaries(self):
    """Test parsing scores at boundary values."""
    assert parse_tfidf_score("0 1234 Test") == 0
    assert parse_tfidf_score("100 1234 Test") == 100

  def test_score_outside_range(self):
    """Test parsing scores outside expected range (with warning)."""
    # Should still parse but log warning
    score = parse_tfidf_score("150 1234 Test")
    assert score == 150

    score = parse_tfidf_score("-10 1234 Test")
    assert score == -10

  def test_mock_script_output_parsing(self):
    """Test parsing actual mock script output."""
    script_path = os.path.join(
      os.path.dirname(__file__),
      'fixtures',
      'mock_search_tfidf.py'
    )

    return_code, stdout, stderr = run_external_script(
      script_path,
      []
    )

    score = parse_tfidf_score(stdout)
    assert score == 42
