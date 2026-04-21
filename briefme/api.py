"""BriefMe-AI FastAPI — serves heartbeat results and before/after comparison.

Endpoints:
  /health           — service health check
  /heartbeat/mock   — run optimized heartbeat with mock inbox
  /heartbeat/real   — run real heartbeat (IMAP + LLM classifier)
  /create-event     — create Google Calendar event from meeting email
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


@app.get("/heartbeat/real")
def heartbeat_real(since_hours: int = 24, limit: int = 10):
    """Run real heartbeat — IMAP fetch + LLM classification."""
    from briefme.real_heartbeat import run_real_heartbeat
    return run_real_heartbeat(since_hours=since_hours, limit=limit)


@app.get("/calendar")
def calendar_events(max_results: int = 15, days_ahead: int = 30):
    """List upcoming Google Calendar events from all calendars."""
    from briefme.calendar_client import list_upcoming_events
    events = list_upcoming_events(max_results=max_results, days_ahead=days_ahead)
    return {"events": events, "count": len(events)}


@app.post("/create-event")
def create_event_endpoint(summary: str, start_time: str, duration: int = 30, description: str = ""):
    """Create a Google Calendar event (Alfred confirms before calling this)."""
    from briefme.calendar_client import create_event
    return create_event(summary=summary, start_time=start_time, duration_minutes=duration, description=description)


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

    # Measure BOTH before and after with real LLM calls — no extrapolation.
    from briefme.client import call_llm

    test_emails = [
        Email(id="t1", subject="Schedule a meeting", sender="owner@example.com",
              date="2026-04-21T10:00:00Z",
              body="Can you schedule a 30-minute meeting next Tuesday at 2pm?",
              snippet="Can you schedule..."),
        Email(id="t2", subject="Quick reminder", sender="owner@example.com",
              date="2026-04-21T10:00:00Z",
              body="Please remind me to submit the expense report by Friday.",
              snippet="Please remind me..."),
        Email(id="t3", subject="FYI budget note", sender="owner@example.com",
              date="2026-04-21T10:00:00Z",
              body="No action needed, just sharing context.",
              snippet="No action needed..."),
    ]

    # --- BEFORE: 3 LLM calls per email (paraphrase + executive + risk) ---
    before_input_total = 0
    before_output_total = 0
    before_per_email = []
    before_llm_calls = 0

    for email in test_emails:
        email_input = 0
        email_output = 0
        content = f"From: {email.sender}\nSubject: {email.subject}\nBody: {email.body}"

        # Call 1: full paraphrase
        call_llm("Paraphrase this email in detail, restating every point.", content, max_tokens=300)
        t = dict(last_token_usage)
        email_input += t.get("input_tokens", 0)
        email_output += t.get("output_tokens", 0)
        before_llm_calls += 1

        # Call 2: executive summary
        call_llm("Write a concise executive summary of this email.", content, max_tokens=200)
        t = dict(last_token_usage)
        email_input += t.get("input_tokens", 0)
        email_output += t.get("output_tokens", 0)
        before_llm_calls += 1

        # Call 3: risk assessment
        call_llm("Assess the risk level of this email: high, medium, low, or none. Explain.", content, max_tokens=200)
        t = dict(last_token_usage)
        email_input += t.get("input_tokens", 0)
        email_output += t.get("output_tokens", 0)
        before_llm_calls += 1

        before_per_email.append({"email_id": email.id, "input_tokens": email_input, "output_tokens": email_output, "llm_calls": 3})
        before_input_total += email_input
        before_output_total += email_output

    # --- AFTER: 1 LLM call per email (combined classify + summarize) ---
    after_input_total = 0
    after_output_total = 0
    after_per_email = []

    for email in test_emails:
        classify_and_summarize(email)
        t = dict(last_token_usage)
        after_per_email.append({"email_id": email.id, **t})
        after_input_total += t.get("input_tokens", 0)
        after_output_total += t.get("output_tokens", 0)

    # Calculate real reductions
    input_reduction = round((1 - after_input_total / before_input_total) * 100, 1) if before_input_total else 0
    output_reduction = round((1 - after_output_total / before_output_total) * 100, 1) if before_output_total else 0

    return {
        "before": {
            "tool_calls": before_tools.tool_call_count,
            "estimated_tokens": before_tools.estimated_tokens,
            "gmail_searches": len([c for c in before_tools.call_log if c["tool"] == "Gmail:Find Email"]),
            "llm_calls_per_email": 3,
            "provider_tokens": {
                "input_tokens": before_input_total,
                "output_tokens": before_output_total,
                "total_llm_calls": before_llm_calls,
                "per_email": before_per_email,
                "note": "Measured: 3 real LLM calls per email (paraphrase + executive + risk)",
            },
        },
        "after": {
            "tool_calls": after_tools.tool_call_count,
            "estimated_tokens": after_tools.estimated_tokens,
            "gmail_searches": len([c for c in after_tools.call_log if c["tool"] == "Gmail:Find Email"]),
            "llm_calls_per_email": 1,
            "provider_tokens": {
                "input_tokens": after_input_total,
                "output_tokens": after_output_total,
                "total_llm_calls": len(test_emails),
                "per_email": after_per_email,
                "note": "Measured: 1 real LLM call per email (combined classify + summarize)",
            },
        },
        "reduction": {
            "tool_calls_pct": round((1 - after_tools.tool_call_count / before_tools.tool_call_count) * 100, 1),
            "workflow_tokens_pct": round((1 - after_tools.estimated_tokens / before_tools.estimated_tokens) * 100, 1),
            "llm_calls_pct": round((1 - len(test_emails) / before_llm_calls) * 100, 1),
            "provider_input_tokens_pct": input_reduction,
            "provider_output_tokens_pct": output_reduction,
            "provider_total_tokens": {
                "before": before_input_total + before_output_total,
                "after": after_input_total + after_output_total,
            },
            "estimated_cost_usd": {
                "before": round((before_input_total * 3 + before_output_total * 15) / 1_000_000, 6),
                "after": round((after_input_total * 3 + after_output_total * 15) / 1_000_000, 6),
                "pricing": "Claude Sonnet 4.6: $3/M input, $15/M output",
                "note": "Output tokens cost 5x more than input. Compact JSON output is the main cost driver reduction.",
            },
        },
    }
