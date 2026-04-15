# backend/app/db/models/notification_outbox.py
"""
Notification outbox — transactional email delivery queue.

Rows are written atomically inside the scan transaction so that a send
failure never causes the scan to fail or a breach alert to be missed on
the next scan cycle.

State machine:
  pending  →  sent      (email delivered, signal.notified_at set)
  pending  →  failed    (all retries exhausted)

Rows are never updated back to pending. Retry logic re-reads pending rows
and increments attempt_count; after MAX_ATTEMPTS the row is marked failed.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, TimestampMixin

MAX_OUTBOX_ATTEMPTS: int = 3


class NotificationOutbox(Base, TimestampMixin):
    __tablename__ = "notification_outbox"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    # signal_id (the deduplication hash string, not the PK uuid)
    signal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # Denormalised for the email template — avoids a join at send time.
    to_email: Mapped[str] = mapped_column(String(320), nullable=False)
    monitored_email: Mapped[str] = mapped_column(String(320), nullable=False)
    template: Mapped[str] = mapped_column(String(64), nullable=False)
    # JSON payload passed directly to the email template renderer.
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", index=True
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_attempted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
