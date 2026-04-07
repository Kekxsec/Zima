# backend/app/providers/tools/mbox_parser/models.py
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


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
    date: datetime | None = None
    # Newsletter / subscription detection headers (RFC 2919, RFC 2369)
    list_id: str | None = None
    list_unsubscribe: str | None = None
    reply_to: str | None = None
