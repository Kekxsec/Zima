# backend/app/db/repositories/auth_tokens.py
"""Auth token repository — implemented in Stage 2."""

from sqlalchemy.ext.asyncio import AsyncSession


class AuthTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
