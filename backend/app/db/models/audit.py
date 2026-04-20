# backend/app/db/models/audit.py
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class AuditEventType:
    # Auth
    SIGN_IN_REQUESTED = "auth.sign_in_requested"
    SIGN_IN_SUCCESS = "auth.sign_in_success"
    SIGN_IN_FAILED = "auth.sign_in_failed"
    OTP_RATE_LIMITED = "auth.otp_rate_limited"

    # Scans
    SCAN_TRIGGERED = "scan.triggered"
    SCAN_COMPLETED = "scan.completed"
    SCAN_FAILED = "scan.failed"

    # Account
    ACCOUNT_CREATED = "account.created"
    ACCOUNT_DELETED = "account.deleted"
    DATA_EXPORTED = "account.data_exported"
    TIER_CHANGED = "account.tier_changed"

    # Assets
    ASSET_VERIFIED = "asset.verified"

    # Findings
    FINDING_SUPPRESSED = "finding.suppressed"
    FINDING_UNSUPPRESSED = "finding.unsuppressed"
    FINDING_RESOLVED = "finding.resolved"
    FINDING_REOPENED = "finding.reopened"
    SIGNAL_SUPPRESSED = "signal.suppressed"

    # Browser extension
    EXTENSION_SETUP_TOKEN_ISSUED = "extension.setup_token_issued"  # noqa: S105
    EXTENSION_REGISTER_SUCCEEDED = "extension.register_succeeded"  # noqa: S105
    EXTENSION_REGISTER_FAILED = "extension.register_failed"  # noqa: S105


class AuditEvent(Base):
    """
    Append-only audit log. Records are never updated or deleted.
    On GDPR erasure requests, the user_id is nulled but the event
    record is retained for security and billing audit purposes.
    """

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    event_metadata: Mapped[dict[str, object]] = mapped_column(
        "metadata", JSON, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_audit_user_time", "user_id", "created_at"),
        Index("ix_audit_type_time", "event_type", "created_at"),
    )
