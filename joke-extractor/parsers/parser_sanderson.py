#!/usr/bin/env python3
"""Parser for Steve Sanderson (aardvark@illinois.edu) joke emails."""

import re
import logging
from .email_data import EmailData, JokeData
from . import register_parser


_SOJ_PREFIXES = (
  "Mikey's Funnies:",
  "Mikey\u2019s Funnies:",  # RIGHT SINGLE QUOTATION MARK variant
  "Mikey\u00e2s Funnies:",  # mojibake variant (â from misencoded UTF-8)
  "Mikeyâs Funnies:",
  "A Joke A Day:",
  "A Joke A Day!",
  "The Good Clean Fun List:",
)


def _can_be_parsed_here(email: EmailData) -> bool:
  """Return True if this email is from Steve Sanderson's aardvark joke list."""
  return "aardvark@illinois.edu" in email.from_header.lower()


def _is_soj(line: str) -> bool:
  """Return True if line is a Start-Of-Joke marker."""
  if line.startswith("*" * 20):
    return True
  return any(line.startswith(prefix) for prefix in _SOJ_PREFIXES)


def _is_eof(line: str) -> bool:
  """Return True if line is the End-Of-Email marker."""
  return line.startswith("Steve Sanderson")


def _title_from_line(line: str) -> str:
  """
  Try to extract a title from a candidate line.

  Strips non-ASCII-printable characters (encoding artifacts such as Â and
  non-breaking spaces) before checking length. Returns line.title() if the
  cleaned result is 1-35 characters, otherwise returns empty string.
  """
  clean = re.sub(r'[^\x20-\x7E]', '', line).strip()
  if clean and len(clean) <= 35:
    return clean.title()
  return ""


def _format_body(lines: list[str]) -> str:
  """
  Format collected HTML lines into joke body text.

  Each non-blank line is treated as a full paragraph (HTML/lynx-dump format).
  Returns non-blank lines joined by double newlines, with outer whitespace stripped.
  """
  paragraphs = [line for line in lines if line.strip()]
  return "\n\n".join(paragraphs).strip()


@register_parser(_can_be_parsed_here)
def parse(email: EmailData) -> list[JokeData]:
  """
  Parse Steve Sanderson joke emails from aardvark@illinois.edu.

  HTML content is preferred; returns [] if HTML is empty.

  Jokes are delimited by SOJ markers (20+ asterisks, 'A Joke A Day:',
  "Mikey's Funnies:", 'The Good Clean Fun List:', etc.) and terminated by
  the 'Steve Sanderson' footer line.

  The title is the first non-blank line after an SOJ if it is <=35
  characters (after stripping encoding artifacts); otherwise title is "".
  """
  if not email.html.strip():
    return []

  jokes = []
  submitter = email.from_header
  lines = email.html.split('\n')

  # States: PREAMBLE, TITLE_SEARCH, COLLECTING
  state = "PREAMBLE"
  current_title = ""
  current_body: list[str] = []

  def _save_joke() -> None:
    body = _format_body(current_body)
    if body:
      jokes.append(JokeData(text=body, submitter=submitter, title=current_title))

  for line in lines:
    stripped = line.strip()

    if _is_eof(stripped):
      if state == "COLLECTING":
        _save_joke()
      break

    if _is_soj(stripped):
      if state == "COLLECTING":
        _save_joke()
      current_title = ""
      current_body = []
      state = "TITLE_SEARCH"
      continue

    if state == "PREAMBLE":
      continue

    if state == "TITLE_SEARCH":
      if not stripped:
        continue
      current_title = _title_from_line(line)
      if not current_title:
        # First content line is too long to be a title; include it in body
        current_body.append(line)
      state = "COLLECTING"
      continue

    current_body.append(line)

  return jokes
