# backend/app/db/repositories/findings.py
import uuid

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.enums import FindingStatus
from backend.app.correlation.models import Finding


class FindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, finding: Finding) -> Finding:
        """
        Inserts or updates a finding by finding_id.
        Repeated correlation runs on the same signal set produce one finding row.
        """
        stmt = (
            pg_insert(Finding)
            .values(
                finding_id=finding.finding_id,
                finding_type=finding.finding_type,
                user_id=finding.user_id,
                severity=finding.severity,
                confidence=finding.confidence,
                title=finding.title,
                explanation=finding.explanation,
                contributing_signal_ids=finding.contributing_signal_ids,
                affected_entity_ids=finding.affected_entity_ids,
                rule_name=finding.rule_name,
                status=FindingStatus.OPEN,
            )
            .on_conflict_do_update(
                constraint="uq_finding_id",
                set_={
                    "status": FindingStatus.OPEN,
                    "explanation": finding.explanation,
                    "contributing_signal_ids": finding.contributing_signal_ids,
                    "updated_at": func.now(),
                },
            )
            .returning(Finding)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def get_open_for_user(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Finding]:
        result = await self.session.execute(
            select(Finding)
            .where(Finding.user_id == user_id, Finding.status == FindingStatus.OPEN)
            .order_by(Finding.created_at.desc())
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
    ) -> list[Finding]:
        result = await self.session.execute(
            select(Finding)
            .where(Finding.user_id == user_id, Finding.status == status)
            .order_by(Finding.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def count_for_user_by_status(self, user_id: uuid.UUID, status: str) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Finding)
            .where(Finding.user_id == user_id, Finding.status == status)
        )
        return result.scalar_one()

    async def get_all_for_user(self, user_id: uuid.UUID) -> list[Finding]:
        result = await self.session.execute(
            select(Finding)
            .where(Finding.user_id == user_id)
            .order_by(Finding.created_at.desc())
        )
        return list(result.scalars().all())

    async def suppress(self, user_id: uuid.UUID, finding_id: str) -> bool:
        """Sets an open finding to suppressed. Returns True if a row was updated."""
        result = await self.session.execute(
            update(Finding)
            .where(
                Finding.finding_id == finding_id,
                Finding.user_id == user_id,
                Finding.status == FindingStatus.OPEN,
            )
            .values(status="suppressed")
            .returning(Finding.id)
        )
        return result.scalar_one_or_none() is not None

    async def unsuppress(self, user_id: uuid.UUID, finding_id: str) -> bool:
        """Restores a suppressed finding to open. Returns True if a row was updated."""
        result = await self.session.execute(
            update(Finding)
            .where(
                Finding.finding_id == finding_id,
                Finding.user_id == user_id,
                Finding.status == "suppressed",
            )
            .values(status=FindingStatus.OPEN)
            .returning(Finding.id)
        )
        return result.scalar_one_or_none() is not None

    async def resolve(self, user_id: uuid.UUID, finding_id: str) -> bool:
        """Marks an open finding as resolved. Returns True if a row was updated."""
        result = await self.session.execute(
            update(Finding)
            .where(
                Finding.finding_id == finding_id,
                Finding.user_id == user_id,
                Finding.status == FindingStatus.OPEN,
            )
            .values(status=FindingStatus.RESOLVED)
            .returning(Finding.id)
        )
        return result.scalar_one_or_none() is not None

    async def reopen(self, user_id: uuid.UUID, finding_id: str) -> bool:
        """Reopens a suppressed or resolved finding.

        Returns True if a row was updated.
        """
        result = await self.session.execute(
            update(Finding)
            .where(
                Finding.finding_id == finding_id,
                Finding.user_id == user_id,
                Finding.status.in_([FindingStatus.SUPPRESSED, FindingStatus.RESOLVED]),
            )
            .values(status=FindingStatus.OPEN)
            .returning(Finding.id)
        )
        return result.scalar_one_or_none() is not None

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        """Hard-deletes all findings for a user. Used by GDPR erasure."""
        await self.session.execute(delete(Finding).where(Finding.user_id == user_id))
