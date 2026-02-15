# Parser Specification (`parser-spec.md`)

> **Version**: 1.1  
> **Purpose**: Developer-ready specification for implementing a new email joke parser.  
> **Prerequisites**: See `parser-interface.md` and `email_data.py`.  
> **Key Principle**: *Parse deterministically, reject silently, log only for debug.*

---
## 0. Provided files Description
`parser-spec2.md` - spec for parser design
`parser-interface.md` - specifies the parser interface to the other parts of the system
`email_data.py` - shared data definitions
`parser-hints.md` - specific rules for how to parse this specific set of emails
`EmailData_*.json` - files that contain the data from parsed emails specific to this email group
---
## 1. Core Interface (Mandatory)

All parsers **must** implement the following two functions with *exact* signatures:

```python
def _can_be_parsed_here(email: EmailData) -> bool:
    """Return True if this parser can parse the email."""
    ...

def parse(email: EmailData) -> list[JokeData]:
    """Parse email and return a list of extracted jokes (possibly empty)."""
    ...
```

- **No optional arguments**, no mutation of inputs.
- Use `from .email_data import EmailData, JokeData`.
- Register via `from . import register_parser` (see §2.4).

---

## 2. Email Content Handling

### 2.1. Text vs. HTML Precedence
| Field | Status | Guidance |
|-------|--------|----------|
| `email.text` | Raw plain-text (from `text/plain` MIME part) | Use only if `email.html` is empty |
| `email.html` | **Already converted to clean text via `lynx`** | **Preferred source** — typically more structured and whitespace-normalized |
| **Default strategy** | `if email.html.strip(): use html; else: use text` |  
| **Do not** | Convert HTML → text yourself (e.g., no `html2text`, `BeautifulSoup`, `re.sub('<.*?>', '', ...)`) |  

> ✅ **Correct**: `lines = email.html.split('\n')`  
> ❌ **Incorrect**: `from html.parser import HTMLParser` or stripping tags manually

### 2.2. Quality of Content
- `email.html` has already been processed for readability (e.g., ` lynx -dump`), so:
  - Paragraphs may be separated by blank lines (`\n\n`).
  - Headers, footers, and UI lines (e.g., “Unsubscribe”) remain distinguishable.
- Parsers should exploit this cleanliness (e.g., use `line.startswith("...")` confidently).

---

## 3. Parser Implementation Rules

### 3.1. Identification (`_can_be_parsed_here`)
- Use `email.from_header`, `email.subject_header`, or both — *case-insensitive*.
- Avoid partial or ambiguous matches (e.g., `"humor"` is too generic).
- **No content inspection** — only headers.

### 3.2. Parsing (`parse`)
- **Always return `list[JokeData]`**, even if `[]`.
- Use `email.html` first → fall back to `email.text`.
- Extract jokes via delimiters, markers, or structural patterns (e.g., `"HUMOR"` → title → content until `<>< `).
- **Title extraction rules** (see `parser-hints.md` for specifics):
  - Typically: *“Next non-blank line ≤35 characters”*.
  - Normalize with `.title()` if title exists; otherwise `""`.
  - If no title line (e.g., next line too long) → `title = ""`.

### 3.3. Whitespace & Formatting
| Convention | Behavior |
|-----------|---------|
| Leading/trailing whitespace | `.strip()` final `joke_text` |
| Internal blank lines | Preserve (e.g., multi-paragraph jokes) |
| Carriage returns (`\r`) | Not expected — if present, treat as whitespace (`line.rstrip()` handles) |

For the TEXT version of a joke, remove '\n' from lines that have no blank line between them. For example:
**BEFORE TEXT:**
```
A woman was scooping up an armload of toaster pastries just as I was
contemplating their ingredients. I said to her, "These things could
kill you."

She said, "Well, they're just for the kids."
```
**AFTER TEXT:**
```
A woman was scooping up an armload of toaster pastries just as I was contemplating their ingredients. I said to her, "These things could kill you."

She said, "Well, they're just for the kids."
```

### 3.4. Error Handling
- **Silent failure**: Missing delimiters, empty content, or malformed input → return `[]`.
- **Optional logging**: Use `logging.warning(...)` *only* for:
  - Unexpected structure (e.g., two start delimiters before first joke ends)
  - Partial parse (e.g., end delimiter missing → extracted to EOF)
- Never log at `INFO` in `_can_be_parsed_here` / `parse`.

---

## 4. Data Contract

| Field | Requirement |
|-------|-------------|
| `EmailData` | Immutable tuple — parsers **must not mutate** |
| `JokeData` | Immutable tuple — always create new instances |
| `joke_submitter` | Raw `email.from_header` (exact string) |
| `joke_title` | As specified in `parser-hints.md` (may be `""`) |
| `joke_text` | Trimmed, with `\n\n` between joke lines |

---

## 5. Hints File Format (`parser-hints.md`) — Mandatory Fields

Every parser *must* include this `parser-hints.md`. **Example** structure:

```markdown
# parser-hints.md for [Parser Name]

## Identification
Pattern (case-insensitive): "substring or regex"
Source fields: `from_header`, `subject_header`, or both  
Example: `"christianvoice.org" in email.from_header.lower()`

## Parsing Logic
Content source preference: `html` (default), `text`, or `auto`
Start delimiter: `"MARKER"` (e.g., line *starts with* this)  
End delimiter: `"END"` (e.g., line *starts with* this)  
Title rule:  
  - Rule: "Next non-blank line ≤35 characters"
  - Case normalization: `title.title()` (or `""` if missing)  
  - If line too long: `title = ""`  
Whitespace handling:  
  - Join lines with `\n`
  - Trim joke text
Multiple jokes per email? `yes` / `no`  
If `no`: exit after first joke

## Edge Cases
- No start delimiter → return `[]`  
- No end delimiter → log warning, extract to EOF  
- Empty email → return `[]`  
```

> 🔔 Note: `parser-hints.md` is **human-only** — parsers must *not* parse this file.

---

## 6. Architecture & Integration

### 6.1. Parser Discovery
- Parsers in `parsers/` directory.
- Auto-registered via `@register_parser(_can_be_parsed_here)` in `parsers/__init__.py`.
- On incoming email:
  1. Iterate registered parsers (most specific first).
  2. Call `_can_be_parsed_here(email)` → first `True` wins.
  3. Call `parse(email)` → collect results.

### 6.2. Statelessness
- All parsers must be **pure functions** — no class state, no global variables, no side effects.
