# backend/app/db/repositories/audit.py
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.audit import AuditEvent


class AuditRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def log(
        self,
        event_type: str,
        user_id: uuid.UUID | None = None,
        ip_address: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        try:
            event = AuditEvent(
                user_id=user_id,
                event_type=event_type,
                ip_address=ip_address,
                event_metadata=metadata or {},
            )
            self.session.add(event)
        except Exception as e:
            from backend.app.core.logging import get_logger

            get_logger(__name__).error("audit.log_failed", error=str(e))

    async def get_for_user(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[AuditEvent]:
        result = await self.session.execute(
            select(AuditEvent)
            .where(AuditEvent.user_id == user_id)
            .order_by(AuditEvent.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
