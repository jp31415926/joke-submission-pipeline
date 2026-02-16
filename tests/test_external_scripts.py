#!/usr/bin/env python3
"""
Tests for external_scripts.py
"""

import os
import subprocess
import pytest
import tempfile
from pathlib import Path

from external_scripts import run_external_script, parse_tfidf_score


class TestRunExternalScript:
  """Tests for run_external_script function."""
  
  def test_simple_echo_command(self):
    """Test running a simple echo command."""
    return_code, stdout, stderr = run_external_script(
      "/bin/echo",
      ["hello", "world"],
      timeout=5
    )
    
    assert return_code == 0
    assert stdout.strip() == "hello world"
    assert stderr == ""
  
  def test_return_code_capture(self):
    """Test capturing non-zero return code."""
    return_code, stdout, stderr = run_external_script(
      "/bin/false",
      [],
      timeout=5
    )
    
    assert return_code == 1
    assert stdout == ""
  
  def test_stdout_capture(self):
    """Test capturing stdout."""
    return_code, stdout, stderr = run_external_script(
      "/bin/echo",
      ["test output"],
      timeout=5
    )
    
    assert return_code == 0
    assert "test output" in stdout
  
  def test_stderr_capture(self):
    """Test capturing stderr."""
    # Use sh to redirect to stderr
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
      f.write("#!/bin/sh\n")
      f.write("echo 'error message' >&2\n")
      script_path = f.name
    
    try:
      os.chmod(script_path, 0o755)
      return_code, stdout, stderr = run_external_script(
        script_path,
        [],
        timeout=5
      )
      
      assert return_code == 0
      assert stdout == ""
      assert "error message" in stderr
    finally:
      os.unlink(script_path)
  
  def test_timeout_handling(self):
    """Test that timeout is enforced."""
    with pytest.raises(subprocess.TimeoutExpired):
      run_external_script(
        "/bin/sleep",
        ["10"],
        timeout=1
      )
  
  def test_nonexistent_script(self):
    """Test error when script doesn't exist."""
    with pytest.raises(FileNotFoundError):
      run_external_script(
        "/nonexistent/script.py",
        [],
        timeout=5
      )
  
  def test_non_executable_script(self):
    """Test error when script is not executable."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
      f.write("#!/usr/bin/env python3\nprint('test')\n")
      script_path = f.name
    
    try:
      # Don't make it executable
      os.chmod(script_path, 0o644)
      
      with pytest.raises(PermissionError):
        run_external_script(script_path, [], timeout=5)
    finally:
      os.unlink(script_path)
  
  def test_mock_tfidf_script(self):
    """Test running the mock TF-IDF script."""
    # Get path to mock script
    tests_dir = Path(__file__).parent
    mock_script = tests_dir / "fixtures" / "mock_search_tfidf.py"
    
    return_code, stdout, stderr = run_external_script(
      str(mock_script),
      [],
      timeout=5
    )
    
    assert return_code == 0
    assert "42 1234 Test Joke Title" in stdout
    assert stderr == ""


class TestParseTfidfScore:
  """Tests for parse_tfidf_score function."""
  
  def test_valid_output(self):
    """Test parsing valid TF-IDF output."""
    output = "91 9278 A Meaningful New Year's Gesture"
    score, funny_id = parse_tfidf_score(output)
    assert score == 91
  
  def test_valid_output_with_newline(self):
    """Test parsing valid output with trailing newline."""
    output = "42 1234 Test Joke Title\n"
    score, funny_id = parse_tfidf_score(output)
    assert score == 42
  
  def test_valid_output_multiple_lines(self):
    """Test parsing output with multiple lines (uses first line)."""
    output = "85 5555 First Joke\n90 6666 Second Joke\n"
    score, funny_id = parse_tfidf_score(output)
    assert score == 85
  
  def test_score_zero(self):
    """Test parsing score of 0."""
    output = "0 1111 No Match"
    score, funny_id = parse_tfidf_score(output)
    assert score == 0
  
  def test_score_hundred(self):
    """Test parsing score of 100."""
    output = "100 2222 Perfect Match"
    score, funny_id = parse_tfidf_score(output)
    assert score == 100
  
  def test_empty_output(self):
    """Test error on empty output."""
    with pytest.raises(ValueError, match="Empty output"):
      parse_tfidf_score("")
  
  def test_whitespace_only_output(self):
    """Test error on whitespace-only output."""
    with pytest.raises(ValueError, match="Empty output"):
      parse_tfidf_score("   \n  ")
  
  def test_invalid_format_missing_parts(self):
    """Test error when output has fewer than 3 parts."""
    with pytest.raises(ValueError, match="Invalid TF-IDF output format"):
      parse_tfidf_score("42 1234")
  
  def test_invalid_format_one_part(self):
    """Test error when output has only one part."""
    with pytest.raises(ValueError, match="Invalid TF-IDF output format"):
      parse_tfidf_score("42")
  
  def test_invalid_score_not_integer(self):
    """Test error when score is not an integer."""
    with pytest.raises(ValueError, match="Invalid TF-IDF score"):
      parse_tfidf_score("abc 1234 Test Joke")
  
  def test_invalid_score_float(self):
    """Test error when score is a float."""
    with pytest.raises(ValueError, match="Invalid TF-IDF score"):
      parse_tfidf_score("42.5 1234 Test Joke")
  
  def test_long_joke_title(self):
    """Test parsing with long joke title containing many words."""
    output = "75 8888 This Is A Very Long Joke Title With Many Words"
    score, funny_id = parse_tfidf_score(output)
    assert score == 75
