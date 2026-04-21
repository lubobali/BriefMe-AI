"""Google Calendar client — creates events from meeting emails.

Uses OAuth2 with lubobali23@gmail.com. Requires:
1. Google Cloud project with Calendar API enabled
2. OAuth credentials (credentials.json) downloaded
3. First-time auth flow to generate token.json
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

load_dotenv()

CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "token.json")
CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")
DEFAULT_TIMEZONE = os.getenv("CALENDAR_TIMEZONE", "America/Chicago")

# Scopes needed for calendar event creation
SCOPES = ["https://www.googleapis.com/auth/calendar.readonly", "https://www.googleapis.com/auth/calendar.events"]


def _get_service():
    """Build authenticated Google Calendar service."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


def create_event(
    summary: str,
    start_time: str,
    duration_minutes: int = 30,
    description: str = "",
    attendee_email: str | None = None,
) -> dict:
    """Create a Google Calendar event.

    Args:
        summary: Event title
        start_time: ISO 8601 datetime string (e.g., "2026-04-22T14:00:00")
        duration_minutes: Event duration (default 30 min)
        description: Event description/notes
        attendee_email: Optional attendee to invite

    Returns:
        dict with event id, link, and status
    """
    service = _get_service()

    start_dt = datetime.fromisoformat(start_time)
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    event_body = {
        "summary": summary,
        "description": description,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": DEFAULT_TIMEZONE,
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": DEFAULT_TIMEZONE,
        },
    }

    if attendee_email:
        event_body["attendees"] = [{"email": attendee_email}]

    event = service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()

    return {
        "id": event.get("id"),
        "link": event.get("htmlLink"),
        "status": "created",
        "summary": summary,
        "start": start_dt.isoformat(),
        "end": end_dt.isoformat(),
    }


def list_upcoming_events(max_results: int = 10, days_ahead: int = 30) -> list[dict]:
    """List upcoming calendar events from ALL calendars."""
    service = _get_service()

    now = datetime.utcnow()
    time_min = now.isoformat() + "Z"
    time_max = (now + timedelta(days=days_ahead)).isoformat() + "Z"

    # Get all calendars the user has access to
    calendar_list = service.calendarList().list().execute()
    calendars = calendar_list.get("items", [])

    all_events = []
    for cal in calendars:
        cal_id = cal.get("id")
        cal_name = cal.get("summary", "Unknown")
        try:
            result = service.events().list(
                calendarId=cal_id,
                timeMin=time_min,
                timeMax=time_max,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            ).execute()

            for e in result.get("items", []):
                all_events.append({
                    "id": e.get("id"),
                    "summary": e.get("summary", "No title"),
                    "start": e.get("start", {}).get("dateTime", e.get("start", {}).get("date")),
                    "end": e.get("end", {}).get("dateTime", e.get("end", {}).get("date")),
                    "calendar": cal_name,
                })
        except Exception:
            continue

    # Sort by start time
    all_events.sort(key=lambda e: e.get("start", ""))
    return all_events[:max_results]
