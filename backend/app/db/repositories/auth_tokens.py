# backend/app/db/repositories/auth_tokens.py
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.models import AuthToken


class AuthTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_valid_token(self, email: str, code_hash: str) -> AuthToken | None:
        """
        Returns a matching token only if it is:
        - Correct email and code_hash
        - Not yet used (used_at IS NULL)
        - Not expired (expires_at > now)
        Returns None for any other condition.
        """
        result = await self.session.execute(
            select(AuthToken)
            .where(
                AuthToken.email == email,
                AuthToken.code_hash == code_hash,
                AuthToken.used_at.is_(None),
                AuthToken.expires_at > datetime.now(UTC),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_active_for_email(self, email: str) -> int:
        """
        Counts tokens for this email that are unused and not yet expired.
        Used to enforce MAX_ACTIVE_TOKENS_PER_EMAIL rate limit.
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(AuthToken)
            .where(
                AuthToken.email == email,
                AuthToken.used_at.is_(None),
                AuthToken.expires_at > datetime.now(UTC),
            )
        )
        return result.scalar_one()

    async def invalidate_all_for_email(self, email: str) -> None:
        """Marks all active tokens for an email as used. Called on account deletion."""
        await self.session.execute(
            update(AuthToken)
            .where(
                AuthToken.email == email,
                AuthToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(UTC))
        )
