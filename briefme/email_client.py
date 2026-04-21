"""Real email client — connects to Namecheap Private Email via IMAP.

Reads emails from data@lubobali.com using IMAP (mail.privateemail.com).
No Gmail API needed, no forwarding, works directly with Namecheap.
"""

from __future__ import annotations

import email
import imaplib
import os
from datetime import datetime, timedelta, timezone
from email.header import decode_header

from dotenv import load_dotenv

from briefme.schemas import Email

load_dotenv()

IMAP_SERVER = os.getenv("IMAP_SERVER", "mail.privateemail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
APPROVED_SENDERS = os.getenv("APPROVED_SENDERS", "").split(",")


def _decode_header_value(value: str) -> str:
    """Decode email header (handles encoded subjects)."""
    if not value:
        return ""
    decoded_parts = decode_header(value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def _extract_body(msg: email.message.Message) -> str:
    """Extract plain text body from email message."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")
        # Fallback: try HTML
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or "utf-8"
                    return payload.decode(charset, errors="replace")[:500]
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            charset = msg.get_content_charset() or "utf-8"
            return payload.decode(charset, errors="replace")
    return ""


def fetch_recent_emails(
    since_hours: int = 24,
    limit: int = 10,
    unread_only: bool = False,
) -> list[Email]:
    """Fetch recent emails via IMAP from Namecheap Private Email.

    Args:
        since_hours: Only fetch emails from the last N hours.
        limit: Max emails to return.
        unread_only: If True, only fetch unread (UNSEEN) emails.

    Returns:
        List of Email objects, newest first.
    """
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        raise ValueError("EMAIL_ADDRESS and EMAIL_PASSWORD must be set in .env")

    mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
    try:
        mail.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        mail.select("INBOX")

        # Build search criteria
        since_date = (datetime.now(timezone.utc) - timedelta(hours=since_hours)).strftime("%d-%b-%Y")
        if unread_only:
            criteria = f'(UNSEEN SINCE {since_date})'
        else:
            criteria = f'(SINCE {since_date})'

        _, message_ids = mail.search(None, criteria)

        if not message_ids[0]:
            return []

        ids = message_ids[0].split()
        # Take most recent N
        ids = ids[-limit:]
        ids.reverse()  # newest first

        results = []
        for msg_id in ids:
            _, msg_data = mail.fetch(msg_id, "(RFC822)")
            if not msg_data or not msg_data[0]:
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            sender = _decode_header_value(msg.get("From", ""))
            subject = _decode_header_value(msg.get("Subject", ""))
            date = msg.get("Date", "")
            body = _extract_body(msg)
            snippet = body[:200].replace("\n", " ").strip()
            email_id = msg.get("Message-ID", str(msg_id))

            results.append(Email(
                id=email_id,
                subject=subject,
                sender=sender,
                date=date,
                body=body,
                snippet=snippet,
            ))

        return results

    finally:
        try:
            mail.logout()
        except Exception:
            pass


def fetch_from_approved_senders(
    since_hours: int = 24,
    limit: int = 10,
) -> list[Email]:
    """Fetch recent emails only from approved senders.

    Filters client-side after IMAP fetch (IMAP FROM search is unreliable
    with display names). Approved senders configured via APPROVED_SENDERS env var.
    """
    all_emails = fetch_recent_emails(since_hours=since_hours, limit=limit * 3)

    if not APPROVED_SENDERS or APPROVED_SENDERS == [""]:
        return all_emails[:limit]

    filtered = []
    for em in all_emails:
        sender_lower = em.sender.lower()
        for approved in APPROVED_SENDERS:
            if approved.strip().lower() in sender_lower:
                filtered.append(em)
                break

    return filtered[:limit]
