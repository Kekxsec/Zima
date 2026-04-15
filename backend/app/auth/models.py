# backend/app/auth/models.py
import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tier: Mapped[str] = mapped_column(String(20), default="core", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_sign_in_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Billing fields — populated when Stripe customer is created
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    # GDPR — consent recorded at first sign-in
    privacy_policy_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # OTP brute-force protection — consecutive failure counter and lockout window
    otp_fail_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    otp_locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    asset_otp_fail_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    asset_otp_locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    session_revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class AuthToken(Base):
    """
    One-time sign-in codes. Single-use, 15-minute expiry.
    The raw code is never stored — only its SHA-256 hash.
    Email is stored here (not on User) because a token may exist
    before the User row does (first sign-in creates User on verify, not request).
    """

    __tablename__ = "auth_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    requested_from_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    __table_args__ = (
        Index("ix_auth_token_email_hash", "email", "code_hash"),
        # Composite index for count_active_for_email and get_valid_token queries
        # which filter by (email, expires_at) with used_at IS NULL condition.
        Index("ix_auth_token_email_expires", "email", "expires_at"),
    )

    @property
    def is_expired(self) -> bool:
        return bool(datetime.now(UTC) > self.expires_at)

    @property
    def is_used(self) -> bool:
        return self.used_at is not None
