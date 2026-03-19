# backend/app/db/repositories/signals.py
import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.enums import SignalStatus
from backend.app.signals.dedup import compute_signal_id
from backend.app.signals.models import Signal
from backend.app.signals.schemas import SignalCreate


class SignalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, data: SignalCreate) -> Signal:
        """
        Atomic insert-or-update. If a signal with the same signal_id
        already exists, it is updated to open status with fresh evidence.
        This prevents duplicate rows on repeated scan runs.
        """
        signal_id = compute_signal_id(data.user_id, data.signal_type, data.entity_id)

        stmt = (
            pg_insert(Signal)
            .values(
                signal_id=signal_id,
                signal_type=data.signal_type,
                category=data.category,
                entity_type=data.entity_type.value,
                entity_id=data.entity_id,
                entity_value=data.entity_value,
                user_id=data.user_id,
                severity=data.severity.value,
                confidence=data.confidence.value,
                source=data.source,
                provider=data.provider,
                summary=data.summary,
                details=data.details,
                evidence=data.evidence,
                tags=data.tags,
                recommended_action=data.recommended_action,
                status=SignalStatus.OPEN,
            )
            .on_conflict_do_update(
                constraint="uq_signal_id",
                set_={
                    "status": SignalStatus.OPEN,
                    "severity": data.severity.value,
                    "evidence": data.evidence,
                    "updated_at": func.now(),
                },
            )
            .returning(Signal)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_open_for_user(
        self,
        user_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Signal]:
        result = await self.session.execute(
            select(Signal)
            .where(Signal.user_id == user_id, Signal.status == SignalStatus.OPEN)
            .order_by(Signal.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_open_for_user(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Signal)
            .where(Signal.user_id == user_id, Signal.status == SignalStatus.OPEN)
        )
        return result.scalar_one()
