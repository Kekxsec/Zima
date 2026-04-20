# backend/app/email_accounts/schemas.py
"""
Internal intermediate schema used during account discovery.
Never persisted directly — feeds into DiscoveredAccountRepository.upsert().
"""

from datetime import datetime

from pydantic import BaseModel


class DiscoveredAccountDraft(BaseModel):
    """
    One candidate account discovered from a single parsed email.
    Produced by AccountDiscoveryService; consumed by the background task.
    """

    service_name: str
    display_name: str
    email_used: str
    source_type: (
        str  # DiscoveredAccountSourceType constant — best type seen across group
    )
    sender_domain: str
    login_url: str | None
    password_reset_url: str | None
    first_seen_at: datetime | None
    last_seen_at: datetime | None
    unsubscribe_url: str | None = None
    email_count: int = 1
    confidence_score: int = (
        0  # 0-100 derived from frequency, source type, registry presence
    )
