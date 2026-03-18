# backend/app/db/repositories/findings.py
"""Finding repository — implemented in Stage 5."""

from sqlalchemy.ext.asyncio import AsyncSession


class FindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
