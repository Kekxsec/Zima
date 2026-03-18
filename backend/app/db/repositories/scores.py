# backend/app/db/repositories/scores.py
"""Score repository — implemented in Stage 5."""

from sqlalchemy.ext.asyncio import AsyncSession


class ScoreRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
