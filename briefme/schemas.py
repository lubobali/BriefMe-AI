"""Pydantic v2 models for BriefMe-AI inputs and outputs."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, field_validator


class Email(BaseModel):
    """An email message from Gmail."""

    id: str
    subject: str
    sender: str
    date: str
    body: str
    snippet: str

    @field_validator("id")
    @classmethod
    def id_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("id must not be empty")
        return v


class EmailClassification(BaseModel):
    """LLM classification + summary of a single email."""

    category: Literal["meeting", "action", "fyi", "skip"]
    summary: str
    risk_level: Literal["high", "medium", "low", "none"]
    extracted_date: str | None = None
    extracted_action: str | None = None
    confidence: float


class Action(BaseModel):
    """An action taken by the heartbeat workflow."""

    type: Literal["calendar_event", "email_forward", "fyi_summary", "skipped"]
    email_id: str
    detail: str


class HeartbeatResult(BaseModel):
    """Result of a complete heartbeat cycle."""

    status: Literal["OK", "HEARTBEAT_OK", "DONE"]
    emails_checked: int
    actions_taken: list[Action]
    token_usage: dict
