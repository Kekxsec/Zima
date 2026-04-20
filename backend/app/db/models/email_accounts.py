# backend/app/db/models/email_accounts.py
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, TimestampMixin


class MboxUploadStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VaultImportStatus:
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class VaultImportType:
    BITWARDEN_JSON = "bitwarden_json"
    PROTON_PASS_JSON = "proton_pass_json"  # noqa: S105
    ONEPASSWORD_1PUX = "1password_1pux"


class DiscoveredAccountSourceType:
    ACCOUNT_CONFIRMATION = "account_confirmation"
    PASSWORD_RESET = "password_reset"  # noqa: S105
    RECEIPT = "receipt"
    NEWSLETTER = "newsletter"
    SECURITY_ALERT = "security_alert"
    EPIEOS = "epieos"
    HOLEHE = "holehe"
    MAIGRET = "maigret"
    PASSWORD_MANAGER = "password_manager"  # noqa: S105
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
    login_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    password_reset_url: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    login_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    password_reset_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    unsubscribe_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    sender_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    email_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_reviewed: Mapped[bool] = mapped_column(nullable=False, default=False)
    # 0-100 score derived from message frequency, source type, and registry presence
    confidence_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # User triage decision: None=pending, confirmed, dismissed, newsletter, receipt
    user_verdict: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # System-assigned category: account | newsletter | receipt | notification
    account_category: Mapped[str | None] = mapped_column(String(20), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "user_id", "service_name", "email_used", name="uq_discovered_account"
        ),
        Index("ix_discovered_account_user", "user_id"),
        Index("ix_discovered_account_user_service", "user_id", "service_name"),
        Index("ix_discovered_account_reviewed", "user_id", "is_reviewed"),
        Index("ix_discovered_account_confidence", "user_id", "confidence_score"),
        Index("ix_discovered_account_category", "user_id", "account_category"),
    )


class NewsletterSubscription(Base, TimestampMixin):
    """
    A newsletter or subscription sender detected in a user's mbox.
    (user_id, sender_domain) is the natural unique key.
    Created by the newsletter detection pre-pass in the mbox processor.
    """

    __tablename__ = "newsletter_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    upload_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    sender_domain: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    unsubscribe_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    list_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "high" | "medium"
    confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="high")
    is_reviewed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_phishing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    recommended_action: Mapped[str] = mapped_column(
        String(50), nullable=False, default="review"
    )

    __table_args__ = (
        UniqueConstraint("user_id", "sender_domain", name="uq_newsletter_subscription"),
        Index("ix_newsletter_subscription_user", "user_id"),
        Index("ix_newsletter_subscription_reviewed", "user_id", "is_reviewed"),
    )


class VaultImport(Base, TimestampMixin):
    """
    Tracks the lifecycle of a user-submitted password manager export file.
    (user_id, file_hash) is the idempotency key.
    Raw file content is NEVER stored here.
    """

    __tablename__ = "vault_imports"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    import_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=VaultImportStatus.PENDING
    )
    accounts_discovered: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_detail: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint("user_id", "file_hash", name="uq_vault_import_user_hash"),
        Index("ix_vault_import_user_status", "user_id", "status"),
    )
