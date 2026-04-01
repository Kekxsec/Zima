# backend/app/correlation/models.py
import uuid

from sqlalchemy import JSON, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, TimestampMixin


class Finding(Base, TimestampMixin):
    __tablename__ = "findings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Deterministic ID — same rule + same contributing signals = same finding_id
    finding_id: Mapped[str] = mapped_column(String(32), nullable=False)
    finding_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )

    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)

    contributing_signal_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    affected_entity_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    rule_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)

    __table_args__ = (
        UniqueConstraint("finding_id", name="uq_finding_id"),
        Index("ix_finding_user_status", "user_id", "status"),
    )
