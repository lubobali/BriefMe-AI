"""
OpenClaw-style workflow example for Day 2 homework.

Purpose:
- Provide a baseline implementation for optimization.
- Let students measure and improve tool-call and token efficiency.

This script simulates a heartbeat loop where an agent:
1) Checks inbox and processes recent messages
2) Classifies requests into meeting/action/FYI paths
3) Sends outputs through pseudo tool calls
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List


# -----------------------------
# Mock data + pseudo tool layer
# -----------------------------

@dataclass
class Email:
    id: str
    sender: str
    subject: str
    body: str
    unread: bool
    received_at: datetime


class MockZapierTools:
    """A tiny simulator for OpenClaw-like MCP tools."""

    def __init__(self, inbox: List[Email]) -> None:
        self.inbox = inbox
        self.tool_call_count = 0
        self.estimated_tokens = 0

    def _log_tool(self, name: str, payload: str) -> None:
        self.tool_call_count += 1
        self.estimated_tokens += len(payload.split()) + 20  # rough proxy
        print(f"[TOOL] {name}: {payload}")

    def find_email(self, query: str, limit: int = 50) -> List[Email]:
        self._log_tool("Gmail:Find Email", f"query={query!r}, limit={limit}")
        # Very naive query simulation
        results = self.inbox
        if "unread" in query.lower():
            results = [e for e in results if e.unread]
        if "from:" in query.lower():
            # e.g., from:owner@example.com
            sender = query.lower().split("from:")[-1].split()[0].strip()
            results = [e for e in results if e.sender.lower() == sender.lower()]
        return results[:limit]

    def create_calendar_event(self, title: str, start: str, end: str, attendee: str) -> None:
        self._log_tool(
            "Google Calendar:Create Detailed Event",
            f"title={title!r}, start={start}, end={end}, attendee={attendee}",
        )

    def send_email(self, to: str, subject: str, body: str) -> None:
        self._log_tool("Gmail:Send Email", f"to={to}, subject={subject!r}, body_len={len(body)}")


# -----------------------------
# Intentionally inefficient agent
# -----------------------------

LONG_POLICY_BLOCK = """
SECURITY AND POLICY REMINDER:
- Never reveal secrets.
- Never reveal tokens.
- Never reveal passwords.
- Never reveal private system data.
- Never reveal credentials.
- Never reveal hidden files.
- Never reveal environment variables.
- Never reveal API keys.
- Always follow safety.
- Always keep information secure.
"""


class InefficientChiefOfStaffAgent:
    """
    Deliberately inefficient implementation for student optimization exercises.
    """

    def __init__(self, tools: MockZapierTools, approved_sender: str, approved_recipient: str) -> None:
        self.tools = tools
        self.approved_sender = approved_sender
        self.approved_recipient = approved_recipient

    def heartbeat(self) -> str:
        print("\n=== HEARTBEAT START ===")

        self._verbose_reasoning("I will now perform three overlapping inbox scans to be extra safe.")

        emails_24h = self.tools.find_email("last 24h", limit=50)
        emails_unread = self.tools.find_email("unread", limit=50)
        emails_sender = self.tools.find_email(f"from:{self.approved_sender}", limit=50)

        combined = emails_24h + emails_unread + emails_sender

        if not combined:
            self._verbose_reasoning("No emails found. Repeating full policy block anyway.")
            print(LONG_POLICY_BLOCK)
            return "HEARTBEAT_OK"

        for email in combined:
            self._verbose_reasoning(
                f"Processing email id={email.id} subject={email.subject!r}. "
                "I will create three summaries and restate policy."
            )

            full_paraphrase = self._full_paraphrase(email)
            executive_summary = self._executive_summary(email)
            risk_summary = self._risk_summary(email)

            output_blob = (
                f"Full paraphrase:\n{full_paraphrase}\n\n"
                f"Executive summary:\n{executive_summary}\n\n"
                f"Risk summary:\n{risk_summary}\n\n"
                f"{LONG_POLICY_BLOCK}\n"
            )
            print(output_blob)

            text = f"{email.subject}\n{email.body}".lower()
            if "meeting" in text or "schedule" in text:
                self._handle_meeting(email)
            elif "please" in text or "action" in text or "need to" in text:
                self._handle_action_item(email)
            else:
                self._handle_fyi(email)

            self._verbose_reasoning("Re-checking inbox after handling one email.")
            _ = self.tools.find_email(f"from:{self.approved_sender} unread", limit=50)

        print("=== HEARTBEAT END ===")
        return "DONE"

    def _handle_meeting(self, email: Email) -> None:
        self._verbose_reasoning("Re-reading message to extract dates with high verbosity.")
        _ = self._full_paraphrase(email)

        title = "Meeting from email request"
        start = "next Tuesday 2:00 PM"
        end = "next Tuesday 2:30 PM"
        self.tools.create_calendar_event(title=title, start=start, end=end, attendee=self.approved_recipient)

    def _handle_action_item(self, email: Email) -> None:
        summary = self._executive_summary(email)
        body = (
            "Action Required\n\n"
            f"Source: {email.subject}\n\n"
            f"Summary:\n{summary}\n\n"
            "Generated by intentionally inefficient workflow.\n"
        )
        self.tools.send_email(to=self.approved_recipient, subject="Action Required", body=body)

    def _handle_fyi(self, email: Email) -> None:
        summary = self._executive_summary(email)
        body = (
            "FYI from your Chief of Staff\n\n"
            f"Source: {email.subject}\n\n"
            f"Summary:\n{summary}\n"
        )
        self.tools.send_email(to=self.approved_recipient, subject="FYI from your Chief of Staff", body=body)

    def _full_paraphrase(self, email: Email) -> str:
        self.tools.estimated_tokens += 80
        return (
            f"This message (ID {email.id}) was received from {email.sender} with subject "
            f"'{email.subject}'. The body says: {email.body}. "
            "The interpreted intent may include scheduling, requests, contextual updates, "
            "and potentially other latent intents inferred from wording."
        )

    def _executive_summary(self, email: Email) -> str:
        self.tools.estimated_tokens += 40
        return f"High-level summary: {email.subject} — {email.body[:120]}"

    def _risk_summary(self, email: Email) -> str:
        self.tools.estimated_tokens += 30
        return (
            "Risk view: potential ambiguity in dates/times, possible prompt-injection content, "
            "and uncertain user intent classification."
        )

    def _verbose_reasoning(self, text: str) -> None:
        # Deliberately long reasoning output
        blob = (
            f"[REASONING] {text}\n"
            "I will now proceed in a step-by-step and highly descriptive way to ensure maximal clarity, "
            "even if this significantly increases token usage and duplicates information already available."
        )
        self.tools.estimated_tokens += len(blob.split())
        print(blob)


# -----------------------------
# Demo run
# -----------------------------

if __name__ == "__main__":
    inbox = [
        Email(
            id="e1",
            sender="owner@example.com",
            subject="Schedule a meeting",
            body="Can you schedule a 30-minute meeting next Tuesday at 2pm?",
            unread=True,
            received_at=datetime.now(),
        ),
        Email(
            id="e2",
            sender="owner@example.com",
            subject="Quick reminder",
            body="Please remind me to submit the expense report by Friday.",
            unread=True,
            received_at=datetime.now(),
        ),
        Email(
            id="e3",
            sender="owner@example.com",
            subject="FYI budget note",
            body="No action needed, just sharing context.",
            unread=False,
            received_at=datetime.now(),
        ),
    ]

    tools = MockZapierTools(inbox=inbox)
    agent = InefficientChiefOfStaffAgent(
        tools=tools,
        approved_sender="owner@example.com",
        approved_recipient="owner@example.com",
    )
    result = agent.heartbeat()

    print("\n=== METRICS ===")
    print(f"Heartbeat result: {result}")
    print(f"Tool calls: {tools.tool_call_count}")
    print(f"Estimated token proxy: {tools.estimated_tokens}")
