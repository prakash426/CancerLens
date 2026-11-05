"""Clinical boundary guard (SEC-03 / FR-06).

Refuses personal diagnosis, symptom triage, treatment selection, drug dosing and
personal clinical-image interpretation with ``OUT_OF_SCOPE_CLINICAL`` while
allowing general educational questions and public claims. Deterministic regex
only; when a text matches both an allow-shaped and a refuse-shaped pattern the
refusal wins (fail safe).
"""

from __future__ import annotations

import re

CLINICAL_REFUSAL_REASON = "Personal medical question (diagnosis, symptoms, treatment or dosing)."

_REASON_TRIAGE = "Personal symptom triage or self-diagnosis question."
_REASON_TREATMENT = "Personal treatment selection or dosing question."
_REASON_IMAGE = "Personal clinical image or test interpretation request."

# Optional adjectives between an article and a symptom noun ("a hard lump").
_ADJ = r"(?:[a-z]+\s+){0,3}?"

_STANDALONE_REFUSE: tuple[tuple[re.Pattern[str], str], ...] = tuple(
    (re.compile(pattern, re.IGNORECASE), reason)
    for pattern, reason in (
        # Personal treatment decisions ("should I take / can I stop ...").
        (
            r"\b(should|can|could|must|shall|need)\s+i\s+"
            r"(take|stop|start|use|get|have|skip|try|switch|continue|avoid)\b",
            _REASON_TREATMENT,
        ),
        # Self-diagnosis questions.
        (r"\bdo\s+i\s+have\b", _REASON_TRIAGE),
        (r"\bam\s+i\s+(at\s+risk|going\s+to\s+die|dying|sick)\b", _REASON_TRIAGE),
        (r"\bwhat\s+stage\s+am\s+i\b", _REASON_TRIAGE),
        (r"\bam\s+i\b.{0,40}\b(stage|terminal|cancer)\b", _REASON_TRIAGE),
        # Drug dosing quantities are out of scope even in general phrasing (PRD boundary).
        (r"\b(what|which)\s+(dose|dosage)\b", _REASON_TREATMENT),
        (r"\bhow\s+(much|many)\s+(mg|milligrams?|mcg|micrograms?|pills?|tablets?|units?|grams?)\b", _REASON_TREATMENT),
        (r"\b\d+\s*(mg|milligrams?|mcg|micrograms?)\b.{0,30}\b(take|dose|daily|twice|per\s+day)\b", _REASON_TREATMENT),
        (r"\b(diagnose|treat)\s+me\b", _REASON_TRIAGE),
        # "My X" possessive clinical nouns (tests, findings, reports, treatment options).
        (
            r"\bmy\s+(biopsy|scan|ct|mri|pet(\s+scan)?|x-?ray|mammogram|pathology|lab|blood\s*test|"
            r"test\s*results?|results?|report|lump|mole|tumou?r|symptoms?|psa(\s+level)?|"
            r"diagnosis|prognosis|treatment(\s+options?)?|prescription|medication)\b",
            _REASON_TRIAGE,
        ),
        # First-person symptom possession ("I found a hard lump ...").
        (
            r"\bi\s+(have|found|noticed|feel|felt|got)\s+(?:a\s+|an\s+)?" + _ADJ
            + r"(lump|mole|pain|bleeding|swelling|symptom|growth|rash|fever|fatigue|cough|"
            r"night\s+sweats|weight\s+loss|discharge)\b",
            _REASON_TRIAGE,
        ),
        # Personal test-result interpretation ("does my PSA level mean stage 3?").
        (
            r"\b(does|do|what\s+do)\s+my\s+(biopsy|pathology|ct|mri|pet(\s+scan)?|mammogram|"
            r"psa(\s+level)?|scan|x-?ray|lab|blood\s*test|test\s*results?)\b.{0,40}"
            r"\b(mean|indicate|show|suggest|stage|diagnos|normal|bad|good)\b",
            _REASON_IMAGE,
        ),
        # Personal clinical-image interpretation without pronouns ("is this mole cancerous?").
        (
            r"\b(is|does)\s+this\s+(mole|lump|lesion|rash|spot|growth|scan|x-?ray|biopsy|slide)\b",
            _REASON_IMAGE,
        ),
        (
            r"\b(interpret|read|analy[sz]e|check)\s+(this|my)\s+"
            r"(scan|ct|mri|x-?ray|mammogram|biopsy|slide|lesion|mole|lab|blood\s*test|report)\b",
            _REASON_IMAGE,
        ),
        (
            r"\bwhat\s+does\s+(this|my)\s+(scan|biopsy|pathology|ct|mri|mammogram|lab|blood\s*test|"
            r"test\s*results?|report)\s+(show|mean|indicate)\b",
            _REASON_IMAGE,
        ),
        # Treatment decisions for a named family member or other person.
        (
            r"\b(should|can|must)\s+(she|he|they)\s+(take|stop|start|skip|switch|try|use|continue)\b",
            _REASON_TREATMENT,
        ),
        (r"\btreatment\b.{0,30}\bright for\b", _REASON_TREATMENT),
        (r"\bright for\s+(me|him|her|them|my\s+\w+)\b", _REASON_TREATMENT),
    )
)


def check_clinical_boundary(text: str) -> tuple[bool, str | None]:
    """Return ``(is_out_of_scope, reason)``. True means refuse with OUT_OF_SCOPE_CLINICAL."""
    lowered_target = text or ""
    for pattern, reason in _STANDALONE_REFUSE:
        if pattern.search(lowered_target):
            return True, reason
    return False, None


__all__ = ["CLINICAL_REFUSAL_REASON", "check_clinical_boundary"]
