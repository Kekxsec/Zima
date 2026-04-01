# backend/app/providers/tools/mbox_parser/models.py
from datetime import datetime

from pydantic import BaseModel


class ParsedEmail(BaseModel):
    """
    Minimal email metadata extracted from a single mbox message.
    Raw body content is NEVER stored — only headers and derived fields.
    """

    message_id: str | None
    subject: str | None
    from_address: str | None
    from_name: str | None
    sender_domain: str | None
    to_address: str | None
    date: datetime | None
