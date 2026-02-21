"""Parser for Bill's Punch Line joke emails."""

import re

from .email_data import EmailData, JokeData
from . import register_parser


def _can_be_parsed_here(email: EmailData) -> bool:
  return "bill@billrayborn.com" in email.from_header.lower()


def _strip_non_alnum_edges(s: str) -> str:
  """Remove non-alphanumeric characters from both ends of a string."""
  return re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', s)


def _build_joke_text(raw_lines: list[str]) -> str:
  """
  Join consecutive non-blank lines into single-line paragraphs.
  Preserve blank lines between paragraphs.
  Reduce multiple consecutive blank lines to one.
  """
  parts = []
  current_para: list[str] = []

  for line in raw_lines:
    if line.strip():
      current_para.append(line.strip())
    else:
      if current_para:
        parts.append(' '.join(current_para))
        current_para = []
      parts.append('')

  if current_para:
    parts.append(' '.join(current_para))

  result: list[str] = []
  prev_blank = False
  for part in parts:
    if part == '':
      if result and not prev_blank:
        result.append('')
      prev_blank = True
    else:
      result.append(part)
      prev_blank = False

  return '\n'.join(result).strip()


@register_parser(_can_be_parsed_here)
def parse(email: EmailData) -> list[JokeData]:
  """
  Parse Bill's Punch Line email format.

  The entire text body (email.text) is the joke. The first non-blank line
  is the title if it contains any alphanumeric characters (non-alphanum
  noise lines like '-- ' or '* *' are skipped with no title). Lines
  containing 'http' or 'mailto' are discarded. Jokes containing
  'copyright' are dropped entirely.

  Parameters
  ----------
  email : EmailData
      Email to parse

  Returns
  -------
  list[JokeData]
      List containing at most one extracted joke.
  """
  if not email.text.strip():
    return []

  lines = email.text.split('\n')
  submitter = email.from_header

  # Find title from the first non-blank line.
  # Lines with alphanum → title (strip non-alphanum edges, then title-case).
  # Lines without alphanum (e.g. '-- ', '* *') → title = '', skip the line.
  title = ''
  content_start = 0
  i = 0
  while i < len(lines):
    stripped = lines[i].strip()
    if stripped:
      if re.search(r'[a-zA-Z0-9]', stripped):
        title = _strip_non_alnum_edges(stripped).title()
      content_start = i + 1
      break
    i += 1

  # Collect joke body, discarding lines with 'http' or 'mailto'.
  joke_lines = []
  for line in lines[content_start:]:
    lower = line.lower()
    if 'http' in lower or 'mailto' in lower:
      continue
    joke_lines.append(line)

  joke_text = _build_joke_text(joke_lines)

  if not joke_text:
    return []

  if 'copyright' in joke_text.lower():
    return []

  return [JokeData(text=joke_text, submitter=submitter, title=title)]
