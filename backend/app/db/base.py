# backend/app/db/base.py
from datetime import UTC, datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        # NOTE: onupdate fires only for ORM single-object updates.
        # Bulk UPDATE statements (session.execute(update(...))) bypass this
        # and will NOT update updated_at automatically. Any bulk update path
        # must set updated_at explicitly.
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
