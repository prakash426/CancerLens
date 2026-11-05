"""PII sanitizer (SG-10 / SEC-06).

Scrubs personal identifiers before any query or canonical claim is processed or
stored. Runs before boundary checks and memory writes. Clinical terms, years
(``2026``) and trial IDs (``NCT01234567``) are preserved.
"""

from __future__ import annotations

import re

_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    # Email addresses.
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[EMAIL]"),
    # Dates of birth ("DOB: 01/02/1970", "born on January 5, 1970").
    (
        re.compile(
            r"\b(?:DOB|date of birth|born on)\s*[:\-]?\s*"
            r"(?:\d{1,2}[/\-.]\d{1,2}[/\-.]\d{2,4}"
            r"|\d{4}[/\-.]\d{1,2}[/\-.]\d{1,2}"
            r"|[A-Z][a-z]+\s+\d{1,2},?\s+\d{4})",
            re.IGNORECASE,
        ),
        "[DOB]",
    ),
    # US Social Security numbers (dashes required, so bare years never match).
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[ID]"),
    # Medical / insurance identifiers (keyword-anchored, so trial IDs never match).
    (
        re.compile(
            r"\b(?:MRN|medical\s+record(?:\s+number)?|patient\s+(?:id|number)|"
            r"member\s+id|account\s+(?:number|no\.?)|policy\s+(?:number|no\.?)|"
            r"policy\s*[:#]|accession(?:\s+(?:number|no\.?))?)\s*[:#]?\s*[\w-]{4,}\b",
            re.IGNORECASE,
        ),
        "[ID]",
    ),
    # International phone numbers ("+44 20 7946 0958"; leading + required).
    (re.compile(r"(?<!\w)\+(?:[\d\s.\-()]*\d){9,15}(?!\w)"), "[PHONE]"),
    # North-American style numbers (10 digits with separators or parens required).
    (
        re.compile(r"(?<!\w)(?:\+?1[\s.\-]?)?(?:\(\d{3}\)|\d{3})[\s.\-]?\d{3}[\s.\-]?\d{4}(?!\w)"),
        "[PHONE]",
    ),
    # First-person name and age introductions.
    (re.compile(r"\bmy name is\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}", re.IGNORECASE), "[REDACTED_PERSON]"),
    (
        re.compile(
            r"\bi am a\s+\d{1,3}\s*-?\s*year\s*-?\s*old\b"
            r"(?:\s+(?:female|male|woman|man|person|patient))?"
            r"(?:\s+named\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)?",
            re.IGNORECASE,
        ),
        "[REDACTED_PERSON]",
    ),
)


def sanitize_pii(text: str) -> str:
    """Replace personal identifiers with stable tokens. Never raises on text input."""
    cleaned = text or ""
    for pattern, replacement in _RULES:
        cleaned = pattern.sub(replacement, cleaned)
    return cleaned


__all__ = ["sanitize_pii"]
