# backend/app/providers/tools/mbox_parser/models.py
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ParsedEmail(BaseModel):
    """
    Minimal email metadata extracted from a single mbox message.
    Raw body content is NEVER stored — only headers and derived fields.
    """

    message_id: str | None = None
    subject: str | None = None
    from_address: str | None = None
    from_name: str | None = None
    sender_domain: str | None = None
    to_address: str | None = None
    to_addresses: list[str] = Field(default_factory=list)
    date: datetime | None = None
    references: list[str] = Field(default_factory=list)
    # Newsletter / subscription detection headers (RFC 2919, RFC 2369)
    list_id: str | None = None
    list_unsubscribe: str | None = None
    precedence: str | None = None
    reply_to: str | None = None
    mime_type: str | None = None
    message_size_bytes: int | None = None
    # Bulk/automated sender signals
    x_feedback_id: str | None = None  # Gmail promotional tab marker
    auto_submitted: str | None = None  # RFC 3834 — "auto-generated" / "auto-replied"
    x_mailer: str | None = None  # Bulk mailer fingerprint
    # Alias-service forwarding headers — set by services like SimpleLogin / AnonAddy
    # when they rewrite the From header before forwarding to the real inbox.
    x_original_from: str | None = None  # X-Original-From / X-Forwarded-From
    x_forwarded_to: str | None = None  # X-Forwarded-To (original To before rewrite)
