"""Real heartbeat — connects to Namecheap IMAP + LLM classifier + Google Calendar.

This is the production version of the mock heartbeat. It:
1. Fetches real emails from data@lubobali.com via IMAP
2. Classifies each with the LLM (1 call per email)
3. Creates Google Calendar events for meetings
4. Returns structured results for Alfred on WhatsApp
"""

from __future__ import annotations

import json
import os

from dotenv import load_dotenv

from briefme.email_client import fetch_from_approved_senders
from briefme.classifier import classify_and_summarize
from briefme.schemas import Email, EmailClassification

load_dotenv()

# Track processed email IDs across heartbeats (persisted to file)
STATE_FILE = os.getenv("BRIEFME_STATE_FILE", "state/processed_ids.json")


def _load_processed_ids() -> set[str]:
    """Load previously processed email IDs from state file."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return set(json.load(f))
    return set()


def _save_processed_ids(ids: set[str]) -> None:
    """Save processed email IDs to state file."""
    os.makedirs(os.path.dirname(STATE_FILE) or ".", exist_ok=True)
    # Keep only last 500 IDs to prevent unbounded growth
    recent = list(ids)[-500:]
    with open(STATE_FILE, "w") as f:
        json.dump(recent, f)


def run_real_heartbeat(since_hours: int = 24, limit: int = 10) -> dict:
    """Run the real heartbeat workflow.

    1. Fetch emails from approved senders via IMAP
    2. Skip already-processed emails
    3. Classify each with LLM
    4. Take action based on classification
    5. Return structured results

    Returns:
        dict with status, emails_checked, actions, and classifications
    """
    processed_ids = _load_processed_ids()

    # 1. Fetch real emails
    emails = fetch_from_approved_senders(since_hours=since_hours, limit=limit)

    if not emails:
        return {
            "status": "HEARTBEAT_OK",
            "emails_checked": 0,
            "new_emails": 0,
            "actions": [],
            "message": "Inbox clear, sir.",
        }

    # 2. Filter out already-processed
    new_emails = [e for e in emails if e.id not in processed_ids]

    if not new_emails:
        return {
            "status": "HEARTBEAT_OK",
            "emails_checked": len(emails),
            "new_emails": 0,
            "actions": [],
            "message": "No new emails since last check.",
        }

    # 3. Classify and act on each new email
    actions = []
    for em in new_emails:
        classification = classify_and_summarize(em)
        processed_ids.add(em.id)

        action = {
            "email_id": em.id,
            "from": em.sender,
            "subject": em.subject,
            "category": classification.category,
            "summary": classification.summary,
            "risk_level": classification.risk_level,
            "confidence": classification.confidence,
        }

        if classification.category == "meeting" and classification.confidence >= 0.7:
            action["action_taken"] = "calendar_event_pending"
            action["extracted_date"] = classification.extracted_date
            action["note"] = "Meeting detected — date extracted for calendar"
            # Calendar event creation happens via /create-event endpoint
            # so Alfred can confirm before creating

        elif classification.category == "action":
            action["action_taken"] = "flagged_action"
            action["extracted_action"] = classification.extracted_action

        elif classification.category == "fyi":
            action["action_taken"] = "noted"

        elif classification.category == "skip":
            action["action_taken"] = "skipped"

        actions.append(action)

    # 4. Save state
    _save_processed_ids(processed_ids)

    # 5. Build summary
    meetings = [a for a in actions if a["category"] == "meeting"]
    action_items = [a for a in actions if a["category"] == "action"]
    fyis = [a for a in actions if a["category"] == "fyi"]
    skipped = [a for a in actions if a["category"] == "skip"]

    return {
        "status": "OK",
        "emails_checked": len(emails),
        "new_emails": len(new_emails),
        "actions": actions,
        "summary": {
            "meetings": len(meetings),
            "action_items": len(action_items),
            "fyis": len(fyis),
            "skipped": len(skipped),
        },
    }
