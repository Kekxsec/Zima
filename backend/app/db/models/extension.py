# backend/app/db/models/extension.py
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, TimestampMixin


class ExtensionSession(Base, TimestampMixin):
    """
    One row per user — tracks the currently registered browser extension.
    One session per user enforced via unique constraint on user_id.
    Multi-browser support is Phase 2.
    """

    __tablename__ = "extension_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    # "chrome" | "brave" | "firefox" | "edge"
    browser: Mapped[str] = mapped_column(String(32), nullable=False)
    extension_version: Mapped[str] = mapped_column(String(32), nullable=False)
    # JWT jti claim for per-token revocation — rotating on re-register
    extension_jti: Mapped[str] = mapped_column(String(64), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_extension_sessions_user_id"),
    )


class ExtensionSnapshot(Base):
    """
    Browser config snapshot collected by the extension on registration and
    periodically thereafter. raw_snapshot is unstructured JSONB — schema
    evolves with the extension version.
    """

    __tablename__ = "extension_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    extension_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("extension_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_extension_snapshots_user_created", "user_id", "created_at"),
    )


class GuidanceEvent(Base):
    """
    Tracks user progress through in-extension step-by-step guides.
    provider: e.g. "gmail" | "outlook" | "yahoo" | "proton" | "fastmail"
    step: e.g. "started" | "step_1" | ... | "mbox_downloaded"
    """

    __tablename__ = "guidance_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    extension_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    step: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_guidance_events_user_provider", "user_id", "provider"),)
