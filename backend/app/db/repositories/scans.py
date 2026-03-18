# backend/app/db/repositories/scans.py
"""Scan repository — implemented in Stage 6."""

from sqlalchemy.ext.asyncio import AsyncSession


class ScanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
