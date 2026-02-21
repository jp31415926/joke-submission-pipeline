"""Parser for Best of Humor emails."""

"""
# PARSER GUIDELINES (DO NOT DELETE)
## Humor_G mailing list

- [x] Text format is preferred
- [ ] HTML format is preferred

- What to do if preferred format is empty?
- [ ] Use other format
- [x] return empty list (e.g. `[]`)

- How many jokes are expected?
- [ ] Only one
- [ ] Specific number:
- [x] Multiple, but no specific number

- Expression to match this parser: `"shawn@bestofhumor.com" in email.from_header.lower()`

- [ ] Yes use `email.subject_header` for the title
- [x] No don't use `email.subject_header` for the title

- The the start of joke marker (SOJ) is a line that 
  - starts with `+--` and ends with `--+` or
  - starts with `++-` and ends with `-++` or 
  - ends with `<<<<` or
  - starts with `------------------------------` (30x'-')

- [x] The rest of the text is the joke text, until you see the end of joke marker (EOJ).

- The EOJ also marks the start of the next joke.

- The end of file marker (EOF) is a line that
  - starts with `~~~~~` or 
  - starts with `_____` or
  - equals `---`
- When the EOF occurs, ignore the remainder of the email.
- If you reach the last line, discard what you have collected.

- [ ] Yes include the markers in the joke
- [x] No don't include the markers in the joke

- Are the paragraphs line wrapped, or one long line?
- [x] Yes - concatenate multiple non-blank lines together into one long line; preserve blank lines between paragraphs.
- [ ] No - insert a blank line between every non-blank line (each like is always a full paragraph).

- [x] Yes reduce multiple consecutive blank lines to one blank line
- [ ] No don't reduce multiple consecutive blank lines to one blank line

## Additional Info
Follow these rules in this order:
- If the first line of the joke contains `http`, discard that line and continue processing the rest of the joke.
- If a joke contains the following strings (case insensitive) on any line in the joke, the entire joke should be discarded:
  - `http`
  - `mailto`
  - `copyright`
- If any line in a joke contains `bestofhumor.com` or `free t-shirt`, discard that line and continue processing the rest of the joke.

"""
from .email_data import EmailData, JokeData
from . import register_parser
import logging


def _can_be_parsed_here(email: EmailData) -> bool:
  return "shawn@bestofhumor.com" in email.from_header.lower()


def _is_soj(line: str) -> bool:
  """Return True if line is a Start-of-Joke (SOJ) marker."""
  s = line.strip()
  return (
    (s.startswith('+--') and s.endswith('--+')) or
    (s.startswith('++-') and s.endswith('-++')) or
    s.endswith('<<<') or
    s.startswith('------------------------------')
  )


def _is_eof(line: str) -> bool:
  """Return True if line is an End-of-File (EOF) marker."""
  s = line.strip()
  return s.startswith('~~~~~') or s.startswith('_____') or s == '---'


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
      current_para.append(line.rstrip())
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


def _collect_joke(joke_lines: list[str], jokes: list[JokeData], submitter: str) -> None:
  """Build joke text from raw lines and append to jokes if it passes filters."""
  if not joke_lines:
    return
  joke_text = _build_joke_text(joke_lines)
  if not joke_text:
    return
  lower = joke_text.lower()
  if 'http' in lower or 'mailto' in lower or 'copyright' in lower:
    return
  jokes.append(JokeData(text=joke_text, submitter=submitter, title=''))


@register_parser(_can_be_parsed_here)
def parse(email: EmailData) -> list[JokeData]:
  """
  Parse 'Best of Humor' email format.

  Jokes are delimited by SOJ marker lines:
    - starts with '+--' and ends with '--+'
    - starts with '++-' and ends with '-++'
    - starts with '>>>' and ends with '<<<'

  Processing stops at EOF markers (starts with '~~~~~' or '_____', or equals '---').
  Jokes containing 'http', 'mailto', or 'copyright' are discarded.

  Parameters
  ----------
  email : EmailData
      Email to parse

  Returns
  -------
  list[JokeData]
      List of extracted jokes.
  """
  if not email.text.strip():
    return []

  jokes: list[JokeData] = []
  submitter = email.from_header
  lines = email.text.split('\n')

  in_joke = False
  joke_lines: list[str] = []
  first_nonblank_seen = False

  for line in lines:
    logging.debug(f"line: {line}")
    if _is_eof(line):
      logging.debug('EOJ')
      if in_joke:
        _collect_joke(joke_lines, jokes, submitter)
      break

    if _is_soj(line):
      logging.debug('SOJ')
      if in_joke:
        _collect_joke(joke_lines, jokes, submitter)
      in_joke = True
      joke_lines = []
      first_nonblank_seen = False
      continue

    if in_joke:
      lower = line.strip().lower()
      if not first_nonblank_seen and lower:
        first_nonblank_seen = True
        if 'http' in lower:
          logging.debug("discard beginning 'http'")
          continue  # discard first line if it contains a URL
      if ('bestofhumor.com' in lower or 'free t-shirt' in lower) and \
          not ('http' in lower or 'mailto' in lower or 'copyright' in lower):
        continue # discard any line if it contains 'bestofhumor.com' or 'free t-shirt'
      joke_lines.append(line)
  else:
    # Loop exhausted without hitting an EOF marker
    if in_joke:
      _collect_joke(joke_lines, jokes, submitter)

  return jokes
