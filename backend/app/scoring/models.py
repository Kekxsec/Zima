# backend/app/scoring/models.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class Score(Base):
    """
    Append-only score record. One row per scan cycle per domain per user.
    Never update — always insert. Query for the latest with ORDER BY calculated_at DESC.
    """

    __tablename__ = "scores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    domain: Mapped[str] = mapped_column(String(50), nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    # Version identifies which scoring model produced this score.
    # Increment when weights or calculator logic changes so historical
    # scores remain explainable and comparable within a version.
    scorer_version: Mapped[str] = mapped_column(
        String(20), default="1.0", nullable=False
    )
    signal_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Link to the scan that produced this score
    scan_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id"), nullable=True
    )

    __table_args__ = (
        Index("ix_score_user_domain_time", "user_id", "domain", "calculated_at"),
    )
