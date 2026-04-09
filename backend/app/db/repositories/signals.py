# backend/app/db/repositories/signals.py
import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.enums import SignalStatus
from backend.app.signals.dedup import compute_signal_id
from backend.app.signals.models import Signal
from backend.app.signals.redaction import redact_evidence
from backend.app.signals.retention import classify_signal, minimise_evidence
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
        signal_id = compute_signal_id(
            data.user_id, data.signal_type, data.entity_id, data.source_ref
        )

        redacted = redact_evidence(data.evidence)
        retention_class = classify_signal(data.signal_type)
        safe_evidence = minimise_evidence(redacted, retention_class)

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
                evidence=safe_evidence,
                tags=data.tags,
                recommended_action=data.recommended_action,
                status=SignalStatus.OPEN,
            )
            .on_conflict_do_update(
                constraint="uq_signal_id",
                set_={
                    "status": SignalStatus.OPEN,
                    "severity": data.severity.value,
                    "evidence": safe_evidence,
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

    async def get_for_user_by_status(
        self,
        user_id: uuid.UUID,
        status: str,
        limit: int = 20,
        offset: int = 0,
        exclude_signal_types: list[str] | None = None,
    ) -> list[Signal]:
        query = select(Signal).where(Signal.user_id == user_id, Signal.status == status)
        if exclude_signal_types:
            query = query.where(Signal.signal_type.not_in(exclude_signal_types))
        result = await self.session.execute(
            query.order_by(Signal.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def count_for_user_by_status(
        self,
        user_id: uuid.UUID,
        status: str,
        exclude_signal_types: list[str] | None = None,
    ) -> int:
        query = (
            select(func.count())
            .select_from(Signal)
            .where(Signal.user_id == user_id, Signal.status == status)
        )
        if exclude_signal_types:
            query = query.where(Signal.signal_type.not_in(exclude_signal_types))
        result = await self.session.execute(query)
        return result.scalar_one()

    async def count_open_for_user(self, user_id: uuid.UUID) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Signal)
            .where(Signal.user_id == user_id, Signal.status == SignalStatus.OPEN)
        )
        return result.scalar_one()

    async def get_all_for_user(self, user_id: uuid.UUID) -> list[Signal]:
        result = await self.session.execute(
            select(Signal)
            .where(Signal.user_id == user_id)
            .order_by(Signal.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_signal_ids_for_user(
        self,
        user_id: uuid.UUID,
        signal_ids: list[str],
    ) -> list[Signal]:
        if not signal_ids:
            return []
        result = await self.session.execute(
            select(Signal).where(
                Signal.user_id == user_id,
                Signal.signal_id.in_(signal_ids),
            )
        )
        return list(result.scalars().all())

    async def suppress(self, user_id: uuid.UUID, signal_id: str) -> bool:
        """Sets an open signal to suppressed. Returns True if a row was updated."""
        result = await self.session.execute(
            update(Signal)
            .where(
                Signal.signal_id == signal_id,
                Signal.user_id == user_id,
                Signal.status == SignalStatus.OPEN,
            )
            .values(status=SignalStatus.SUPPRESSED)
            .returning(Signal.id)
        )
        return result.scalar_one_or_none() is not None

    async def get_breached_entity_values_for_user(
        self, user_id: uuid.UUID
    ) -> frozenset[str]:
        """
        Returns the set of entity_value strings (email addresses) that have at
        least one open breach-related signal for this user.  Used to overlay
        breach status onto discovered accounts at export time.
        """
        result = await self.session.execute(
            select(Signal.entity_value)
            .where(
                Signal.user_id == user_id,
                Signal.signal_type.in_(
                    ["email_breached", "credential_exposure", "stealer_log_exposure"]
                ),
            )
            .distinct()
        )
        return frozenset(v for v in result.scalars().all() if v)

    async def mark_notified(self, signal_id: str) -> None:
        """Sets notified_at on a signal so it is not re-queued for notification."""
        from datetime import UTC, datetime

        await self.session.execute(
            update(Signal)
            .where(Signal.signal_id == signal_id)
            .values(notified_at=datetime.now(UTC))
        )

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        """Hard-deletes all signals for a user. Used by GDPR erasure."""
        await self.session.execute(delete(Signal).where(Signal.user_id == user_id))
