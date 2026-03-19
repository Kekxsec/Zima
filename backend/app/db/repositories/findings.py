# backend/app/db/repositories/findings.py
import uuid

from sqlalchemy import func, select
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
