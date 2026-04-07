# backend/app/db/models/integrations.py
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class IntegrationProvider:
    SIMPLELOGIN = "simplelogin"
    ADDY_IO = "addy_io"


class UserIntegration(Base):
    """
    Per-user API key storage for action providers (SimpleLogin, Addy.io, etc.).

    The api_key field stores an encrypted secret (encryption handled at the
    application layer before persist — this model stores the ciphertext only).

    (user_id, provider) is the natural unique key — one key per provider per user.
    """

    __tablename__ = "user_integrations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    # Encrypted API key ciphertext — never store plaintext
    api_key_ciphertext: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_user_integration"),
        Index("ix_user_integration_user", "user_id"),
    )
