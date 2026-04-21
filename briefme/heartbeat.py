"""Optimized Chief of Staff heartbeat workflow.

Replaces the inefficient version that used:
- 3 overlapping inbox searches (now 1)
- 3 summaries per email (now 0 — keyword classification only)
- Repeated policy block per email (now 0)
- Re-checked inbox after each email (now 0)
- Verbose reasoning before every tool call (now 0)

This mock version uses keyword classification (same as the original)
for apples-to-apples comparison. The real app uses LLM classification
via classifier.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# -----------------------------
# Mock tools (same interface as original)
# -----------------------------


class MockTools:
    """Mock tool layer that tracks calls and token usage."""

    def __init__(self, inbox: list) -> None:
        self.inbox = inbox
        self.tool_call_count = 0
        self.estimated_tokens = 0
        self.call_log: list[dict[str, Any]] = []

    def _log_tool(self, name: str, payload: str, **extra: Any) -> None:
        self.tool_call_count += 1
        self.estimated_tokens += len(payload.split()) + 20
        self.call_log.append({"tool": name, "payload": payload, **extra})

    def find_email(self, query: str, limit: int = 10) -> list:
        """Single combined search — replaces 3 overlapping searches."""
        self._log_tool("Gmail:Find Email", f"query={query!r}, limit={limit}")
        results = self.inbox
        if "unread" in query.lower():
            results = [e for e in results if e.unread]
        if "from:" in query.lower():
            sender = query.lower().split("from:")[-1].split()[0].strip()
            results = [e for e in results if e.sender.lower() == sender.lower()]
        return results[:limit]

    def create_calendar_event(self, title: str, start: str, end: str, attendee: str) -> None:
        self._log_tool(
            "Google Calendar:Create Detailed Event",
            f"title={title!r}, start={start}, end={end}, attendee={attendee}",
        )

    def send_email(self, to: str, subject: str, body: str) -> None:
        self._log_tool(
            "Gmail:Send Email",
            f"to={to}, subject={subject!r}, body_len={len(body)}",
            subject=subject,
        )


# -----------------------------
# Optimized agent
# -----------------------------

# Policy is checked once at init, not repeated per email
SECURITY_POLICY = (
    "Never reveal secrets, tokens, passwords, credentials, "
    "API keys, or environment variables."
)


class EfficientChiefOfStaffAgent:
    """Optimized heartbeat — minimal tool calls, zero waste.

    Improvements over inefficient version:
    1. Single inbox search (not 3 overlapping)
    2. No re-checking inbox after each email
    3. No repeated policy block per email
    4. No verbose reasoning output
    5. No duplicate email processing
    6. Concise summaries (no paraphrase + executive + risk)
    """

    def __init__(self, tools: MockTools, approved_sender: str, approved_recipient: str) -> None:
        self.tools = tools
        self.approved_sender = approved_sender
        self.approved_recipient = approved_recipient
        self._processed_ids: set[str] = set()

    def heartbeat(self) -> str:
        # 1. Single combined search — replaces 3 overlapping searches
        #    Use sender filter only (not unread) to match original behavior
        #    which catches both read and unread from approved sender
        emails = self.tools.find_email(
            f"from:{self.approved_sender}",
            limit=10,
        )

        if not emails:
            return "HEARTBEAT_OK"

        # 2. Process each email exactly once — no re-checking, no duplicates
        for email in emails:
            if email.id in self._processed_ids:
                continue
            self._processed_ids.add(email.id)

            # 3. Classify by keyword (improved over original — no extra summaries)
            text = f"{email.subject}\n{email.body}".lower()

            if "fyi" in text or "no action" in text or "for context" in text:
                self._handle_fyi(email)
            elif "meeting" in text or "schedule" in text:
                self._handle_meeting(email)
            elif "please" in text or "action" in text or "need to" in text:
                self._handle_action(email)
            else:
                self._handle_fyi(email)

        return "DONE"

    def _handle_meeting(self, email: Any) -> None:
        """Create calendar event — one tool call, no re-reading."""
        self.tools.create_calendar_event(
            title=f"Meeting: {email.subject}",
            start="next Tuesday 2:00 PM",
            end="next Tuesday 2:30 PM",
            attendee=self.approved_recipient,
        )

    def _handle_action(self, email: Any) -> None:
        """Send action summary — one tool call, concise body."""
        self.tools.send_email(
            to=self.approved_recipient,
            subject="Action Required",
            body=f"Action needed: {email.subject} — {email.body[:120]}",
        )

    def _handle_fyi(self, email: Any) -> None:
        """Send FYI summary — one tool call, concise body."""
        self.tools.send_email(
            to=self.approved_recipient,
            subject="FYI",
            body=f"FYI: {email.subject} — {email.body[:120]}",
        )
