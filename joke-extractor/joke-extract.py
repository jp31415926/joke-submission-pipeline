#!/usr/bin/env python3
"""
Script to extract joke content from email files, supporting multiple joke email formats.
Supports parsing:
- "You Make Me Laugh" emails (CrosswalkMail)
- Steve Sanderson's "Sunday Fun Stuff" emails
Prioritizes `text/plain` over `text/html`, and cleans up content before output.

Usage:
    python joke-extract.py <email_file> <output_directory>
"""

import sys
import os
import email
import tempfile
import logging
import subprocess

# Configure logging to stderr for visibility in pipelines
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s %(levelname)s %(name)s:%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Import parsers dynamically
from parsers import get_parser, EmailData, JokeData

def parse_email(file_path: str):
    """
    Parse an email file into a Python `email.message.Message` object.

    Parameters
    ----------
    file_path : str
        Path to the email file (must be UTF-8 encoded text).

    Returns
    -------
    email.message.Message
        Parsed email message object.

    Raises
    ------
    SystemExit
        Exits with status code 1 and logs error if parsing fails.
    """
    try:
        #with open(file_path, 'r', encoding='utf-8') as file:

        with open(file_path, 'r', encoding='ISO-8859-1') as file:
            return email.message_from_file(file)
    except Exception as e:
        logging.error(f"Failed to parse email: {e}")
        print(f"502 Failed to parse email: {e}")
        sys.exit(1)


def cleanup_subject(subject: str) -> str:
    """
    Clean email subject by stripping common prefixes (RE:, FW:, FWD:) and trimming whitespace.

    Handles multiple prefixes (e.g., "Re: Re: ..." → "original subject") via iteration.

    Parameters
    ----------
    subject : str
        Raw subject line.

    Returns
    -------
    str
        Cleaned subject without leading prefixes and trailing/leading whitespace.
    """
    subject = subject.strip()
    prefixes = ["re:", "fw:", "fwd:"]  # case-insensitive handling via `.lower()`

    while True:
        original_length = len(subject)
        for prefix in prefixes:
            if subject.lower().startswith(prefix):
                subject = subject[len(prefix):].strip()
                break  # only remove one prefix per iteration
        if len(subject) == original_length:
            break

    return subject


def cleanup_body(text_content: str) -> str:
    """
    Clean up raw email body text by:
    1. Removing leading `>` (reply/quote) markers per line.
    2. Collapsing multiple blank lines to single blank line.
    3. Stripping leading/trailing blank lines.

    Parameters
    ----------
    text_content : str
        Raw text content (not split into lines yet).

    Returns
    -------
    str
        Cleaned text with consistent line breaks and no quote artifacts.
    """
    lines = text_content.split('\n')

    # Pass 1: Strip leading '>' from lines (support nested quotes like ">>")
    for i in range(len(lines)):
        line = lines[i].lstrip()
        while line.startswith('>'):
            line = line[1:].lstrip()
        lines[i] = line

    # Pass 2: Collapse multiple blank lines → single blank line
    i = 0
    prev = "."
    while i < len(lines):
        if lines[i] == '' and prev == '':
            del lines[i]  # remove duplicate blank line
        else:
            prev = lines[i]
            i += 1

    # Pass 3: Remove leading/trailing blank lines
    while lines and lines[0].strip() == '':
        lines.pop(0)
    while lines and lines[-1].strip() == '':
        lines.pop()

    return '\n'.join(lines)


def extract_text_content(email_message) -> str:
    """
    Extract all `text/plain` parts from an email, joining with `-=+=-\n` separators.

    Parameters
    ----------
    email_message : email.message.Message
        Parsed email object.

    Returns
    -------
    str
        List with one string per joined part (often a list of one element).
        Content is cleaned via `cleanup_body`.
    """
    text = ""

    for part in email_message.walk():
        if part.get_content_type() == 'text/plain':
            payload = part.get_payload(decode=True)
            if payload:
                #text_content = payload.decode('utf-8').strip()
                text_content = payload.decode('ISO-8859-1').strip()
                if text_content:
                    # if text:
                    #     text += "-=+=-\n"
                    text += cleanup_body(text_content)

    return text


def extract_html_content(email_message) -> str:
    """
    Extract and convert `text/html` parts to plain text via `lynx`, then clean.

    Uses `subprocess` to invoke:
        lynx -stdin -dump -nolist -nonumbers -nounderline -width=1024 -trim_blank_lines

    Parameters
    ----------
    email_message : email.message.Message
        Parsed email object.

    Returns
    -------
    list of str
        List with one string per converted part, joined with `-=+=-\n`.
        Content is cleaned via `cleanup_body`.
    """
    text = ""

    for part in email_message.walk():
        if part.get_content_type() == 'text/html':
            payload = part.get_payload(decode=True)
            if payload:
                #html_content = payload.decode('utf-8').strip()
                html_content = payload.decode('ISO-8859-1').strip()
                try:
                    process = subprocess.run(
                        ["lynx", "-stdin", "-dump", "-nolist", "-hiddenlinks=ignore",
                         "-nomargins", "-nonumbers", "-nounderline", "-width=1024",
                         "-trim_blank_lines"],
                        input=html_content,
                        text=True,
                        capture_output=True,
                        check=True
                    )
                    text_content = process.stdout.strip()
                    if text_content:
                        if text:
                            text += "-=+=-\n"
                        text += cleanup_body(text_content)
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    logging.warning(f"Failed to convert HTML with lynx: {e}")

    return text


def main():
    """
    Entry point for email joke extraction.

    Command-line arguments:
        $1 : path to email file
        $2 : output directory for extracted jokes

    Each extracted joke is written to a temporary file in `output_dir`,
    with `From:` and `Subject:` headers prepended.

    Exit Codes:
        100 : success (joke extracted)
        200 : no joke found
        500 : argument error
        501 : file not found
        502 : email parsing error
    """
    if len(sys.argv) != 4:
        print("500 Usage: joke-extract.py <email_file> <output_success_dir> <output_failure_dir>")
        sys.exit(1)

    from parsers import _parser_registry
    logging.info(f"Loaded {len(_parser_registry)} parsers")

    email_file = sys.argv[1]
    output_success_dir = sys.argv[2]
    output_failure_dir = sys.argv[3]

    # Validate email file existence
    if not os.path.exists(email_file):
        logging.error(f"Email file does not exist: {email_file}")
        print(f"501 Email file does not exist: {email_file}")
        sys.exit(1)

    # Parse the email
    email_message = parse_email(email_file)

    # Extract text and HTML versions
    text_content = extract_text_content(email_message)
    html_content = extract_html_content(email_message)
    logging.info(f"Text: {len(text_content)} HTML: {len(html_content)}")

    if text_content == html_content:
        logging.info("Text and HTML are identical.")

    if text_content or html_content:
        email = EmailData(
            text = text_content,
            html = html_content,
            from_header = email_message.get('From', '').strip(),
            subject_header = cleanup_subject(email_message.get('Subject', '').strip())
        )

        # Try to find a custom parser
        logging.info(f"From: {email.from_header}")
        jokes = []
        parser = get_parser(email)
        if parser:
            try:
                jokes = parser(email)
            except Exception as e:
                logging.exception(f"Parser failed for {email_file}: {e}")
        else:
            logging.warning("No parser found to process this email")

        if len(jokes) > 0:
            # Write each joke to a temp file in output dir
            for joke in jokes:
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    prefix='joke_',
                    suffix='.txt',
                    dir=output_success_dir,
                    delete=False
                ) as tmp_file:
                    tmp_file.write(f"Title: {joke.title}\n")
                    tmp_file.write(f"Submitter: {joke.submitter}\n")
                    tmp_file.write("\n")  # separator
                    tmp_file.write(joke.text)

                logging.info(f"Successfully extracted joke to {tmp_file.name}")
            print(f"100 Successfully extracted {len(jokes)} joke(s)")
        else:
            # if we didn't get any jokes out of the email, dump the whole email out to a file for further study
            with tempfile.NamedTemporaryFile(
                mode='w',
                prefix='email_',
                suffix='.json',
                dir=output_failure_dir,
                delete=False
            ) as tmp_file:
                tmp_file.write("{\n")
                tmp_file.write(f"  \"subject\": \"{email.subject_header.replace('"', '\\"')}\",\n")
                tmp_file.write(f"  \"from\": \"{email.from_header.replace('"', '\\"')}\",\n")
                tmp_file.write(f"  \"plain_text\": \"{email.text.replace('"', '\\"').replace("\n", "\\n")}\",\n")
                tmp_file.write(f"  \"html_text\": \"{email.html.replace('"', '\\"').replace("\n", "\\n")}\"\n")
                tmp_file.write("}\n")
            tmp_file.close()

            with tempfile.NamedTemporaryFile(
                mode='w',
                prefix='email_',
                suffix='.txt',
                dir=output_failure_dir,
                delete=False
            ) as tmp_file:
                tmp_file.write(f"Subject: {email.subject_header}\n")
                tmp_file.write(f"From: {email.from_header}\n")
                tmp_file.write("\n")
                tmp_file.write(f"-=+=- PLAIN -=+=-\n{email.text}\n")
                tmp_file.write(f"-=+=- HTML -=+=-\n{email.html}\n")
            tmp_file.close()

            logging.info(f"201 No joke found in email with Subject: {email.subject_header}. Written to {tmp_file.name}")
            print(f"201 No joke found in email with Subject: {email.subject_header}. Written to {tmp_file.name}")

    else:
        logging.info("200 No email content found")
        print("200 No email content found")


if __name__ == "__main__":
    main()
