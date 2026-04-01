# backend/app/jobs/models.py
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.core.enums import ScanStatus
from backend.app.db.base import Base, TimestampMixin


class Scan(Base, TimestampMixin):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default=ScanStatus.PENDING, nullable=False, index=True
    )
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    signals_created: Mapped[int] = mapped_column(Integer, default=0)
    findings_created: Mapped[int] = mapped_column(Integer, default=0)
    domains_run: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    target_emails: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    error_detail: Mapped[str | None] = mapped_column(String(1024), nullable=True)
