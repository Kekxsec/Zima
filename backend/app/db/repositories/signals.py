# backend/app/db/repositories/signals.py
"""Signal repository — implemented in Stage 3."""

from sqlalchemy.ext.asyncio import AsyncSession


class SignalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
