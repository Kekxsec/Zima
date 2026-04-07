# backend/app/db/repositories/notification_outbox.py
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.notification_outbox import (
    MAX_OUTBOX_ATTEMPTS,
    NotificationOutbox,
)


class NotificationOutboxRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def enqueue(
        self,
        user_id: uuid.UUID,
        signal_id: str,
        to_email: str,
        monitored_email: str,
        template: str,
        payload: dict[str, Any],
    ) -> NotificationOutbox:
        """
        Write a pending outbox row within the current transaction.

        The row is committed by the caller's session.commit() call —
        it is not flushed or committed here.
        """
        row = NotificationOutbox(
            user_id=user_id,
            signal_id=signal_id,
            to_email=to_email,
            monitored_email=monitored_email,
            template=template,
            payload=payload,
            status="pending",
        )
        self.session.add(row)
        return row

    async def get_pending_for_user(
        self,
        user_id: uuid.UUID,
        limit: int = 10,
    ) -> list[NotificationOutbox]:
        """Return pending rows with remaining attempts, oldest-first."""
        result = await self.session.execute(
            select(NotificationOutbox)
            .where(
                NotificationOutbox.user_id == user_id,
                NotificationOutbox.status == "pending",
                NotificationOutbox.attempt_count < MAX_OUTBOX_ATTEMPTS,
            )
            .order_by(NotificationOutbox.created_at.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def mark_sent(self, row_id: uuid.UUID) -> None:
        await self.session.execute(
            update(NotificationOutbox)
            .where(NotificationOutbox.id == row_id)
            .values(
                status="sent",
                sent_at=datetime.now(UTC),
                last_attempted_at=datetime.now(UTC),
            )
        )

    async def mark_failed(self, row_id: uuid.UUID, error: str) -> None:
        await self.session.execute(
            update(NotificationOutbox)
            .where(NotificationOutbox.id == row_id)
            .values(
                status="failed",
                last_attempted_at=datetime.now(UTC),
                error_detail=error[:1024],
            )
        )

    async def increment_attempt(self, row_id: uuid.UUID) -> None:
        """Increment attempt_count and update last_attempted_at on failure."""
        result = await self.session.execute(
            select(NotificationOutbox).where(NotificationOutbox.id == row_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            return
        row.attempt_count += 1
        row.last_attempted_at = datetime.now(UTC)
        if row.attempt_count >= MAX_OUTBOX_ATTEMPTS:
            row.status = "failed"
            row.error_detail = (row.error_detail or "") + " [max attempts reached]"

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        """Hard-deletes all outbox rows for a user. Used by GDPR erasure."""
        from sqlalchemy import delete

        await self.session.execute(
            delete(NotificationOutbox).where(NotificationOutbox.user_id == user_id)
        )
