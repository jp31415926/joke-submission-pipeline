# Joke Submission Pipeline — Developer Specification

## 1. Overview

This pipeline processes joke submissions from emails into the MariaDB master database. It is **batch-oriented, file-based**, and uses independent stages to transform submissions into a ready-for-review state.

---

## 2. Environment

* Single Linux machine
* Python 3.x
* Local LLM available for cleanliness, formatting, categorization, title generation
* MariaDB is the master joke database
* Cron used for batch orchestration

---

## 3. File-Based State Machine

### 3.1 Directory Structure

Directory names are specified in the `config.py` file. Scripts should not hard code directory names, but instead use config.py variables.
Example: main incoming stage directory would be `os.path.join(config.PIPELINE_MAIN, config.STAGES["incoming"])`

project-root/
├── joke-pipeline.py             # Primary script
├── joke-extractor/               
│   └── joke-extract.py          # joke extract script
├── jokematch2/                  
│   ├── build_tfidf.py           # joke dedup TF-IDF vector builder script
│   └── search_tfidf.py          # joke dedup search script
├── pipeline-main/               # MAIN pipeline top level directory
│   ├── 01_incoming/             # Newly arrived jokes from Maildir
│   ├── 02_parsed/               # Post email parsing
│   ├── 03_deduped/              # After duplicate check
│   ├── 04_clean_checked/        # After cleanliness check
│   ├── 05_formatted/            # After grammar/punctuation formatting
│   ├── 06_categorized/          # After category assignment
│   ├── 07_titled/               # After title assignment
│   ├── 08_ready_for_review/     # Completed jokes ready for human review
│   ├── 09_complete/             # Final storage after review
│   ├── 50_rejected_parse/       # Failed parsing
│   ├── 51_rejected_duplicate/   # Failed duplicate check
│   ├── 52_rejected_cleanliness/ # Failed cleanliness check
│   ├── 53_rejected_format/      # Failed formatting
│   ├── 54_rejected_category/    # Failed category assignment
│   └── 55_rejected_titled/      # Failed title assignment
├── pipeline-priority/           # PRIORITY pipeline top level directory
│   ├── 01_incoming/             # Newly arrived jokes from Maildir
│   ├── 02_parsed/               # Post email parsing
│   ├── 03_deduped/              # After duplicate check
│   ├── 04_clean_checked/        # After cleanliness check
│   ├── 05_formatted/            # After grammar/punctuation formatting
│   ├── 06_categorized/          # After category assignment
│   ├── 07_titled/               # After title assignment
│   ├── 08_ready_for_review/     # Completed jokes ready for human review
│   ├── 09_complete/             # Final storage after review
│   ├── 50_rejected_parse/       # Failed parsing
│   ├── 51_rejected_duplicate/   # Failed duplicate check
│   ├── 52_rejected_cleanliness/ # Failed cleanliness check
│   ├── 53_rejected_format/      # Failed formatting
│   ├── 54_rejected_category/    # Failed category assignment
│   └── 55_rejected_titled/      # Failed title assignment
└── tests/
    ├── test_abc.py
    └── ...


**Pipeline-Priority:**

* Mirrors the `pipeline-main/` structure
* Scripts check `pipeline-priority/` first for files
* Files in `pipeline-priority/` remain independent of `pipeline-main/`

---

### 3.2 File Format (Plain Text + Header)

Each joke candidate is a **single text file**, named by UUID:

```
<Joke-ID>.txt
```

Header structure (key: value), followed by blank line separator:

```
Joke-ID: 550e8400-e29b-41d4-a716-446655440000
Submission-Date: 2026-02-14
From-Name: John Doe
From-Email: john@example.com
Source-Email-File: 1700000000.M1234.mailbox
Pipeline-Stage: 07_titled
Duplicate-Score: 42
Duplicate-Threshold: 70
Cleanliness-Status: PASS
Cleanliness-Confidence: 0.85
Format-Status: PASS
Format-Confidence: 0.92
Categories: Animals, Wordplay
Category-Confidence: 0.77
Title: Why the Chicken Crossed the Road
Rejection-Reason:

Why did the chicken cross the road?
To get to the other side!
```

**Notes:**

* **Title field MAY be blank** until `titled/` stage if missing
* **Duplicate score** from `search_tfidf.py` (0–100)
* All metadata stored inline, including LLM confidence scores
* Files are named with **UUID** for uniqueness

---

## 4. Pipeline Stages & Integration

### 4.1 Stage Summary

| Stage                    | Input                | Processing                                                   | Output               | Rejection                | Integration Notes                                                                      |
| ------------------------ | -------------------- | ------------------------------------------------------------ | -------------------- | ------------------------ | -------------------------------------------------------------------------------------- |
| **01_incoming/**         | Maildir email        | Call `joke-extract.py <email_file> <success_dir> <fail_dir>` | 02_parsed/           | 50_rejected_parse/       | Called **once per email file**; directories passed via `config.py`                     |
| **02_parsed/**           | 01_incoming/         | Duplicate check using `search_tfidf.py <joke_file>`          | 03_deduped/          | 51_rejected_duplicate/   | `search_tfidf.py` output 0–100; threshold (70) in `config.py`; score written to header |
| **03_deduped/**          | 02_parsed/           | Cleanliness LLM                                              | 04_clean_checked/    | 52_rejected_cleanliness/ | Confidence stored in header                                                            |
| **04_clean_checked/**    | 03_deduped/          | Formatting LLM                                               | 05_formatted/        | 53_rejected_format/      | Confidence stored in header                                                            |
| **05_formatted/**        | 04_clean_checked/    | Categorization LLM                                           | 06_categorized/      | 54_rejected_category/    | Confidence stored in header                                                            |
| **06_categorized/**      | 05_formatted/        | Title generation LLM (only if `Title` is blank)              | 07_titled/           | 55_rejected_titled/      | Skips jokes with existing title                                                        |
| **07_titled/**           | 06_categorized/      | Prepare for review                                           | 08_ready_for_review/ | 55_rejected_titled/      | Titles added to header                                                                 |
| **08_ready_for_review/** | 07_titled/           | Manual review                                                | 09_complete/         | N/A                      | Ready for DB insertion                                                                 |
| **09_complete/**         | 08_ready_for_review/ | Insert into MariaDB                                          | 09_complete/         | N/A                      | Archive/complete storage                                                               |

---

### 4.2 Existing Script Execution

* **joke extractor script**

  * `joke-extractor/joke-extract.py` called **once per email** (path to script specified in `config.py` file)
  * Arguments: `<email_file> <success_dir> <fail_dir>`
  * Pipeline wrapper reads stage directories from `config.py` and passes to script
  * Files written to success or fail directories

* **joke match scripts**

  * `jokematch2/build_tfidf.py` run **3am weekdays** via cron  (path to script specified in `config.py` file)
  * `jokematch2/search_tfidf.py <joke_file>` called by deduplication stage
  * Output 0–100; threshold from `config.py` (default 70)
  * Wrapper converts to PASS/FAIL and stores score in file header

---

### 4.3 Multi-Joke Emails

* Each joke extracted becomes a **separate file**
* Each joke is processed independently through all stages

---

### 4.4 Error Handling

* Failures logged in **per-stage log**
* Files remain in input directory for manual inspection
* Manual reinjection only

---

### 4.5 Logging

* Logs include: start/stop timestamps, files processed, errors, skips
* Logs rotatable
* Logging paths configurable in `config.py`
* log verbosity set in `config.py`, default to INFO

---

### 4.6 Cron Orchestration

* Separate cron job per stage
* LLM stages may run slower; independent stages prevent blocking
* Pipeline-priority checked first for files, then pipeline-main
* Build TF-IDF scheduled 3am weekdays

---

## 5. LLM Integration

* Stages: Cleanliness, Formatting, Categorization, Titled
* Confidence scores written inline
* Title generated **only if blank**

---

## 6. MariaDB Integration

* Insert jokes from `ready_for_review/` → `complete/`
* Map metadata fields to DB schema
* Categories mapped to legacy integer fields
* Flags inferred from pipeline stage statuses

---

## 7. Manual Intervention & Reinjection

* Manual review in `ready_for_review/`
* Rejected jokes remain in reject directories
* Reinjection **manual only**
* UUID ensures no collisions

---

## 8. Complete Directory

* `09_complete/` is where complete and reviewed jokes end up
* Another script will insert them into the database
* Stores all metadata and joke content

---

## 9. Config File (`config.py`)

Example structure:

```python
# Directory paths
PIPELINE_MAIN = "/path/to/pipeline-main"
PIPELINE_PRIORITY = "/path/to/pipeline-priority"

STAGES = {
    "incoming": "01_incoming",
    "parsed": "02_parsed",
    "deduped": "03_deduped",
    "clean_checked": "04_clean_checked",
    "formatted": "05_formatted",
    "categorized": "06_categorized",
    "titled": "07_titled",
    "ready_for_review": "08_ready_for_review",
    "complete": "09_complete",
}

REJECTS = {
    "parse": "50_rejected_parse",
    "duplicate": "51_rejected_duplicate",
    "cleanliness": "52_rejected_cleanliness",
    "format": "53_rejected_format",
    "category": "54_rejected_category",
    "titled": "55_rejected_titled",
}

# Script paths
JOKE_EXTRACTOR = "/path/to/joke-extractor/joke-extract.py"
BUILD_TFIDF = "/path/to/jokematch2/build_tfidf.py"
SEARCH_TFIDF = "/path/to/jokematch2/search_tfidf.py"

# Thresholds
DUPLICATE_THRESHOLD = 70  # out of 100

# LLM parameters
LLM_MODEL = "local-llm"
LLM_BATCH_SIZE = 1
LLM_TEMPERATURE = 0.7

# Logging
LOG_DIR = "/path/to/logs"

# Other constants
MAX_RETRIES = 0
```

* All scripts read paths and parameters from `config.py`
* Easy to change directories, thresholds, or script paths without modifying pipeline scripts

---

## 10. Testing Plan

* Test with small batch of emails in `pipeline-main/` and `pipeline-priority/`
* Verify stage transitions, metadata, duplicate scoring, title generation
* Confirm atomic moves, logging, and LLM confidence updates
* Inspect reject directories and complete storage
