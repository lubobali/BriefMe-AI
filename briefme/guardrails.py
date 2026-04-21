"""PII redaction and prompt injection detection for email content."""

from __future__ import annotations

import re

# PII patterns — same proven patterns from DevTrack-AI
PII_PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[EMAIL]"),
    (re.compile(r"\d{3}[-.\s]?\d{3}[-.\s]?\d{4}"), "[PHONE]"),
    (re.compile(r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"), "[IP]"),
    (re.compile(r"sk-[a-zA-Z0-9_-]{10,}|ghp_[a-zA-Z0-9]{10,}|nvapi-[a-zA-Z0-9_-]{10,}"), "[API_KEY]"),
]

# Prompt injection indicators
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?(prior|previous|above)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"new\s+instructions?\s*:", re.IGNORECASE),
    re.compile(r"system\s*prompt\s*:", re.IGNORECASE),
]


def redact_pii(text: str) -> str:
    """Replace PII patterns with placeholder tokens."""
    for pattern, replacement in PII_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def check_prompt_injection(text: str) -> bool:
    """Check if text contains prompt injection attempts."""
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            return True
    return False
