"""Email classifier — ONE LLM call to classify + summarize an email."""

from __future__ import annotations

import json
import os

from briefme.client import call_llm
from briefme.guardrails import redact_pii, check_prompt_injection
from briefme.schemas import Email, EmailClassification


def _load_prompt() -> str:
    """Load classifier prompt from claude_skills/email_classifier.md."""
    prompt_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "claude_skills",
        "email_classifier.md",
    )
    with open(prompt_path) as f:
        return f.read()


def _parse_json_response(text: str) -> dict:
    """Parse JSON from LLM response, stripping markdown fences if present."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        cleaned = "\n".join(lines).strip()
    return json.loads(cleaned)


def classify_and_summarize(email: Email) -> EmailClassification:
    """Classify and summarize an email in ONE LLM call.

    Steps:
    1. Redact PII from email content
    2. Check for prompt injection
    3. Call LLM with classifier prompt
    4. Parse JSON response into EmailClassification
    """
    # Redact PII before sending to LLM
    safe_subject = redact_pii(email.subject)
    safe_body = redact_pii(email.body)

    # Check for prompt injection
    if check_prompt_injection(email.body) or check_prompt_injection(email.subject):
        return EmailClassification(
            category="skip",
            summary="Flagged: possible prompt injection detected",
            risk_level="high",
            confidence=1.0,
        )

    system_prompt = _load_prompt()
    user_content = f"From: {email.sender}\nSubject: {safe_subject}\nBody: {safe_body}"

    response = call_llm(system_prompt, user_content, max_tokens=300)
    data = _parse_json_response(response)

    return EmailClassification(**data)
