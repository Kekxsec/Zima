# backend/app/db/models/companion.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, TimestampMixin


class CompanionSession(Base, TimestampMixin):
    """
    One row per user — tracks the currently registered companion binary.
    machine_id is AES-256-GCM encrypted via encrypt_field().
    One-session-per-user enforced via unique constraint on user_id.
    Multi-device support is Phase 2.
    """

    __tablename__ = "companion_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    # SHA-256 of stable platform hardware ID, encrypted with encrypt_field()
    machine_id: Mapped[str] = mapped_column(String(512), nullable=False)
    # "darwin" | "linux" | "windows"
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    companion_version: Mapped[str] = mapped_column(String(32), nullable=False)
    # JWT jti claim for per-token revocation
    companion_jti: Mapped[str] = mapped_column(String(64), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("user_id", name="uq_companion_sessions_user_id"),
        Index("ix_companion_sessions_user_id", "user_id"),
    )


class BrowserSnapshot(Base):
    """
    Raw snapshot collected by the companion daemon every 5 minutes.
    raw_snapshot is unstructured JSONB — schema evolves with the companion.
    """

    __tablename__ = "browser_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    companion_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    raw_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_browser_snapshots_user_id", "user_id"),
        Index("ix_browser_snapshots_user_created", "user_id", "created_at"),
    )
