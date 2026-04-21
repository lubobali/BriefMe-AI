"""BriefMe-AI FastAPI — serves heartbeat results and before/after comparison.

Endpoints:
  /health           — service health check
  /heartbeat/mock   — run optimized heartbeat with mock inbox
  /compare          — before vs after metrics side by side
"""

from __future__ import annotations

import sys
import os
from dataclasses import dataclass
from datetime import datetime

from fastapi import FastAPI

from briefme.heartbeat import EfficientChiefOfStaffAgent, MockTools

app = FastAPI(title="BriefMe-AI", version="1.0")


# -----------------------------
# Mock email data (same as homework test set)
# -----------------------------

@dataclass
class MockEmail:
    id: str
    sender: str
    subject: str
    body: str
    unread: bool
    received_at: datetime


def _standard_inbox() -> list[MockEmail]:
    """The 4 homework test emails."""
    return [
        MockEmail("e1", "owner@example.com", "Schedule a meeting",
                  "Can you schedule a 30-minute meeting next Tuesday at 2pm?",
                  True, datetime.now()),
        MockEmail("e2", "owner@example.com", "Quick reminder",
                  "Please remind me to submit the expense report by Friday.",
                  True, datetime.now()),
        MockEmail("e3", "owner@example.com", "FYI budget note",
                  "No action needed, just sharing context.",
                  False, datetime.now()),
    ]


# -----------------------------
# Inefficient agent (for comparison)
# -----------------------------

LONG_POLICY_BLOCK = "SECURITY POLICY: " + "Never reveal secrets. " * 10


class InefficientAgent:
    """Original wasteful version — for before/after metrics only."""

    def __init__(self, tools: MockTools, approved_sender: str, approved_recipient: str) -> None:
        self.tools = tools
        self.approved_sender = approved_sender
        self.approved_recipient = approved_recipient

    def heartbeat(self) -> str:
        self._verbose("Three overlapping inbox scans.")
        emails_24h = self.tools.find_email("last 24h", limit=50)
        emails_unread = self.tools.find_email("unread", limit=50)
        emails_sender = self.tools.find_email(f"from:{self.approved_sender}", limit=50)
        combined = emails_24h + emails_unread + emails_sender

        if not combined:
            self._verbose("No emails.")
            self.tools.estimated_tokens += len(LONG_POLICY_BLOCK.split())
            return "HEARTBEAT_OK"

        for email in combined:
            self._verbose(f"Processing {email.id}")
            self.tools.estimated_tokens += 80 + 40 + 30  # 3 summaries
            self.tools.estimated_tokens += len(LONG_POLICY_BLOCK.split())  # policy

            text = f"{email.subject}\n{email.body}".lower()
            if "meeting" in text or "schedule" in text:
                self.tools.estimated_tokens += 80
                self.tools.create_calendar_event("Meeting", "TBD", "TBD", "owner@example.com")
            elif "please" in text or "action" in text or "need to" in text:
                self.tools.estimated_tokens += 40
                self.tools.send_email("owner@example.com", "Action Required", f"Summary: {email.subject}")
            else:
                self.tools.estimated_tokens += 40
                self.tools.send_email("owner@example.com", "FYI", f"FYI: {email.subject}")

            self._verbose("Re-checking inbox.")
            self.tools.find_email(f"from:{self.approved_sender} unread", limit=50)

        return "DONE"

    def _verbose(self, text: str) -> None:
        blob = f"[REASONING] {text} Proceeding step-by-step with maximal clarity."
        self.tools.estimated_tokens += len(blob.split())


# -----------------------------
# Endpoints
# -----------------------------

@app.get("/health")
def health():
    return {"status": "healthy", "service": "BriefMe-AI"}


@app.get("/heartbeat/mock")
def heartbeat_mock():
    """Run optimized heartbeat with standard mock inbox."""
    tools = MockTools(inbox=_standard_inbox())
    agent = EfficientChiefOfStaffAgent(tools, "owner@example.com", "owner@example.com")
    result = agent.heartbeat()

    return {
        "status": result,
        "tool_calls": tools.tool_call_count,
        "estimated_tokens": tools.estimated_tokens,
        "actions": [c for c in tools.call_log if c["tool"] != "Gmail:Find Email"],
    }


@app.get("/compare")
def compare():
    """Run both inefficient and optimized, return side-by-side metrics.

    Includes both workflow proxy tokens (from MockTools) and
    provider-reported LLM tokens (from a real classifier call on
    a sample email) for complete transparency.
    """
    from briefme.classifier import classify_and_summarize
    from briefme.schemas import Email
    from briefme.client import last_token_usage

    # Before (inefficient)
    before_tools = MockTools(inbox=_standard_inbox())
    before_agent = InefficientAgent(before_tools, "owner@example.com", "owner@example.com")
    before_agent.heartbeat()

    # After (optimized)
    after_tools = MockTools(inbox=_standard_inbox())
    after_agent = EfficientChiefOfStaffAgent(after_tools, "owner@example.com", "owner@example.com")
    after_agent.heartbeat()

    # Real LLM classifier call for provider token measurement
    # The inefficient version would call LLM 3x per email (paraphrase + exec + risk)
    # The optimized version calls LLM 1x per email (combined classify + summarize)
    sample_email = Email(
        id="sample",
        subject="Schedule a meeting",
        sender="owner@example.com",
        date="2026-04-21T10:00:00Z",
        body="Can you schedule a 30-minute meeting next Tuesday at 2pm?",
        snippet="Can you schedule...",
    )
    classify_and_summarize(sample_email)
    provider_tokens_per_email = dict(last_token_usage)

    inbox_size = len(_standard_inbox())

    return {
        "before": {
            "tool_calls": before_tools.tool_call_count,
            "estimated_tokens": before_tools.estimated_tokens,
            "gmail_searches": len([c for c in before_tools.call_log if c["tool"] == "Gmail:Find Email"]),
            "llm_calls_per_email": 3,
            "provider_tokens_estimate": {
                "input_tokens": provider_tokens_per_email.get("input_tokens", 0) * 3 * inbox_size,
                "output_tokens": provider_tokens_per_email.get("output_tokens", 0) * 3 * inbox_size,
                "note": "3 LLM calls/email x 3 emails (paraphrase + executive + risk)",
            },
        },
        "after": {
            "tool_calls": after_tools.tool_call_count,
            "estimated_tokens": after_tools.estimated_tokens,
            "gmail_searches": len([c for c in after_tools.call_log if c["tool"] == "Gmail:Find Email"]),
            "llm_calls_per_email": 1,
            "provider_tokens_per_email": provider_tokens_per_email,
            "provider_tokens_estimate": {
                "input_tokens": provider_tokens_per_email.get("input_tokens", 0) * inbox_size,
                "output_tokens": provider_tokens_per_email.get("output_tokens", 0) * inbox_size,
                "note": "1 LLM call/email x 3 emails (combined classify + summarize)",
            },
        },
        "reduction": {
            "tool_calls_pct": round((1 - after_tools.tool_call_count / before_tools.tool_call_count) * 100, 1),
            "workflow_tokens_pct": round((1 - after_tools.estimated_tokens / before_tools.estimated_tokens) * 100, 1),
            "llm_calls_pct": round((1 - 1 / 3) * 100, 1),
        },
    }
