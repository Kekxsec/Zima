# backend/app/db/models/email_accounts.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, TimestampMixin


class MboxUploadStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DiscoveredAccountSourceType:
    ACCOUNT_CONFIRMATION = "account_confirmation"
    PASSWORD_RESET = "password_reset"  # noqa: S105
    RECEIPT = "receipt"
    NEWSLETTER = "newsletter"
    SECURITY_ALERT = "security_alert"
    EPIEOS = "epieos"
    HOLEHE = "holehe"
    MAIGRET = "maigret"
    OTHER = "other"


class ServiceRegistry(Base):
    """
    Curated catalog of known services with their login and password reset URLs.
    Seeded via scripts/seed_service_registry.py. Never auto-generated.
    """

    __tablename__ = "service_registry"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    common_domains: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list
    )
    login_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    password_reset_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_service_registry_name", "service_name"),
        Index("ix_service_registry_active", "is_active"),
    )


class MboxUpload(Base, TimestampMixin):
    """
    Tracks the lifecycle of a user-submitted mbox file.
    (user_id, file_hash) is the idempotency key.
    Raw file content is NEVER stored here.
    """

    __tablename__ = "mbox_uploads"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=MboxUploadStatus.PENDING
    )
    accounts_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    signals_created: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_detail: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("user_id", "file_hash", name="uq_mbox_upload_user_hash"),
        Index("ix_mbox_upload_user_status", "user_id", "status"),
    )


class DiscoveredAccount(Base, TimestampMixin):
    """
    A service/account discovered by scanning inbox data or provider results.
    (user_id, service_name, email_used) is the natural unique key.
    Raw email bodies are NEVER stored here.
    """

    __tablename__ = "discovered_accounts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    upload_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    service_name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email_used: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    login_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    password_reset_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    sender_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    email_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_reviewed: Mapped[bool] = mapped_column(nullable=False, default=False)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "service_name", "email_used", name="uq_discovered_account"
        ),
        Index("ix_discovered_account_user", "user_id"),
        Index("ix_discovered_account_user_service", "user_id", "service_name"),
        Index("ix_discovered_account_reviewed", "user_id", "is_reviewed"),
    )
