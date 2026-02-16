#!/usr/bin/env python3
"""
Tests for ollama_client.py - Ollama LLM integration.
"""

import os
import sys
import json
import pytest
import requests
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ollama_client import OllamaClient


@pytest.fixture
def ollama_config():
  """Sample Ollama configuration."""
  return {
    'OLLAMA_API_URL': 'http://localhost:11434/api/generate',
    'OLLAMA_MODEL': 'llama3',
    'OLLAMA_SYSTEM_PROMPT': 'You are a helpful assistant.',
    'OLLAMA_USER_PROMPT': 'Process this: {content}',
    'OLLAMA_KEEP_ALIVE': 0,
    'OLLAMA_OPTIONS': {
      'temperature': 0.7,
      'num_ctx': 65536,
    }
  }


@pytest.fixture
def client(ollama_config):
  """Create OllamaClient instance."""
  return OllamaClient(ollama_config)


def test_client_initialization(client, ollama_config):
  """Test client initialization."""
  assert client.api_url == ollama_config['OLLAMA_API_URL']
  assert client.model == ollama_config['OLLAMA_MODEL']
  assert client.system_prompt == ollama_config['OLLAMA_SYSTEM_PROMPT']
  assert client.user_prompt_template == ollama_config['OLLAMA_USER_PROMPT']
  assert client.options == ollama_config['OLLAMA_OPTIONS']


@patch('requests.post')
def test_generate_success(mock_post, client):
  """Test successful generate call."""
  # Mock successful response
  mock_response = Mock()
  mock_response.status_code = 200
  mock_response.json.return_value = {
    'response': 'This is a test response'
  }
  mock_post.return_value = mock_response

  # Call generate
  result = client.generate('System prompt', 'User prompt')

  # Verify result
  assert result == 'This is a test response'

  # Verify request was made correctly
  mock_post.assert_called_once()
  call_args = mock_post.call_args
  assert call_args[0][0] == client.api_url
  request_body = call_args[1]['json']
  assert request_body['model'] == 'llama3'
  assert request_body['prompt'] == 'User prompt'
  assert request_body['system'] == 'System prompt'
  assert request_body['stream'] is False


@patch('requests.post')
def test_generate_timeout(mock_post, client):
  """Test generate with timeout."""
  # Mock timeout
  mock_post.side_effect = requests.Timeout()

  # Call generate and expect TimeoutError
  with pytest.raises(TimeoutError):
    client.generate('System prompt', 'User prompt')


@patch('requests.post')
def test_generate_network_error(mock_post, client):
  """Test generate with network error."""
  # Mock network error
  mock_post.side_effect = requests.RequestException('Connection failed')

  # Call generate and expect RequestException
  with pytest.raises(requests.RequestException):
    client.generate('System prompt', 'User prompt')


@patch('requests.post')
def test_generate_rate_limit(mock_post, client):
  """Test generate with rate limiting."""
  # Mock 429 response
  mock_response = Mock()
  mock_response.status_code = 429
  mock_response.raise_for_status.side_effect = requests.HTTPError()
  mock_post.return_value = mock_response

  # Call generate and expect RequestException
  with pytest.raises(requests.RequestException):
    client.generate('System prompt', 'User prompt')


@patch('requests.post')
def test_generate_invalid_json(mock_post, client):
  """Test generate with invalid JSON response."""
  # Mock invalid JSON response
  mock_response = Mock()
  mock_response.status_code = 200
  mock_response.json.side_effect = json.JSONDecodeError('Invalid', '', 0)
  mock_post.return_value = mock_response

  # Call generate and expect ValueError
  with pytest.raises(ValueError):
    client.generate('System prompt', 'User prompt')


@patch('requests.post')
def test_generate_missing_response_field(mock_post, client):
  """Test generate with missing response field."""
  # Mock response without 'response' field
  mock_response = Mock()
  mock_response.status_code = 200
  mock_response.json.return_value = {'other_field': 'value'}
  mock_post.return_value = mock_response

  # Call generate and expect ValueError
  with pytest.raises(ValueError):
    client.generate('System prompt', 'User prompt')


def test_parse_structured_response_json(client):
  """Test parsing JSON response."""
  response_text = json.dumps({
    'status': 'PASS',
    'confidence': 85,
    'reason': 'Clean joke'
  })

  result = client.parse_structured_response(
    response_text,
    ['status', 'confidence', 'reason']
  )

  assert result['status'] == 'PASS'
  assert result['confidence'] == '85'
  assert result['reason'] == 'Clean joke'


def test_parse_structured_response_json_case_insensitive(client):
  """Test parsing JSON with case-insensitive keys."""
  response_text = json.dumps({
    'Status': 'PASS',
    'Confidence': 85
  })

  result = client.parse_structured_response(
    response_text,
    ['status', 'confidence']
  )

  assert result['status'] == 'PASS'
  assert result['confidence'] == '85'


def test_parse_structured_response_key_value(client):
  """Test parsing key-value format."""
  response_text = """
Status: PASS
Confidence: 92
Reason: This is a clean joke
"""

  result = client.parse_structured_response(
    response_text,
    ['Status', 'Confidence', 'Reason']
  )

  assert result['Status'] == 'PASS'
  assert result['Confidence'] == '92'
  assert result['Reason'] == 'This is a clean joke'


def test_parse_structured_response_mixed_case(client):
  """Test parsing with mixed case key-value pairs."""
  response_text = """
status: FAIL
Confidence: 45
"""

  result = client.parse_structured_response(
    response_text,
    ['status', 'Confidence']
  )

  assert result['status'] == 'FAIL'
  assert result['Confidence'] == '45'


def test_parse_structured_response_partial_match(client):
  """Test parsing with some missing keys."""
  response_text = """
Status: PASS
"""

  result = client.parse_structured_response(
    response_text,
    ['Status', 'Confidence', 'Reason']
  )

  assert result['Status'] == 'PASS'
  assert 'Confidence' not in result
  assert 'Reason' not in result


def test_extract_confidence_success(client):
  """Test extracting confidence score."""
  response_dict = {
    'status': 'PASS',
    'confidence': '85'
  }

  confidence = client.extract_confidence(response_dict)
  assert confidence == 85


def test_extract_confidence_case_variations(client):
  """Test extracting confidence with different key cases."""
  # Test 'Confidence'
  result = client.extract_confidence({'Confidence': '90'})
  assert result == 90

  # Test 'score'
  result = client.extract_confidence({'score': '75'})
  assert result == 75

  # Test 'Score'
  result = client.extract_confidence({'Score': '80'})
  assert result == 80


def test_extract_confidence_out_of_range(client):
  """Test extracting confidence out of valid range."""
  # Too high
  result = client.extract_confidence({'confidence': '150'})
  assert result is None

  # Negative
  result = client.extract_confidence({'confidence': '-10'})
  assert result is None


def test_extract_confidence_invalid_value(client):
  """Test extracting confidence with invalid value."""
  # Non-integer
  result = client.extract_confidence({'confidence': 'high'})
  assert result is None

  # Float string
  result = client.extract_confidence({'confidence': '85.5'})
  assert result is None


def test_extract_confidence_missing(client):
  """Test extracting confidence when not present."""
  result = client.extract_confidence({'status': 'PASS'})
  assert result is None


def test_extract_confidence_edge_cases(client):
  """Test extracting confidence at boundaries."""
  # 0 is valid
  result = client.extract_confidence({'confidence': '0'})
  assert result == 0

  # 100 is valid
  result = client.extract_confidence({'confidence': '100'})
  assert result == 100
