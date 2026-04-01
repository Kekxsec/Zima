# backend/app/db/repositories/scores.py
import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.scoring.models import Score


class ScoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert(
        self,
        user_id: uuid.UUID,
        domain: str,
        score: int,
        signal_count: int,
        scan_id: uuid.UUID | None = None,
        scorer_version: str = "1.0",
    ) -> Score:
        """Always insert — never update. Historical scores are immutable."""
        record = Score(
            user_id=user_id,
            domain=domain,
            score=score,
            signal_count=signal_count,
            scorer_version=scorer_version,
            scan_id=scan_id,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_latest_for_user(self, user_id: uuid.UUID) -> list[Score]:
        """Returns the most recent score per domain for a user."""
        subq = (
            select(Score.domain, func.max(Score.calculated_at).label("max_ts"))
            .where(Score.user_id == user_id)
            .group_by(Score.domain)
            .subquery()
        )
        result = await self.session.execute(
            select(Score)
            .join(
                subq,
                (Score.domain == subq.c.domain)
                & (Score.calculated_at == subq.c.max_ts),
            )
            .where(Score.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_all_for_user(self, user_id: uuid.UUID) -> list[Score]:
        result = await self.session.execute(
            select(Score)
            .where(Score.user_id == user_id)
            .order_by(Score.calculated_at.desc())
        )
        return list(result.scalars().all())

    async def delete_all_for_user(self, user_id: uuid.UUID) -> None:
        """Hard-deletes all scores for a user. Used by GDPR erasure."""
        await self.session.execute(delete(Score).where(Score.user_id == user_id))

    async def get_history_for_domain(
        self,
        user_id: uuid.UUID,
        domain: str,
        limit: int = 30,
    ) -> list[Score]:
        """Returns score history for trend charts."""
        result = await self.session.execute(
            select(Score)
            .where(Score.user_id == user_id, Score.domain == domain)
            .order_by(Score.calculated_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
