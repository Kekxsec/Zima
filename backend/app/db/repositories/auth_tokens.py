# backend/app/db/repositories/auth_tokens.py
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.models import AuthToken


class AuthTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, token: AuthToken) -> None:
        """Persist a new AuthToken. Caller must commit after this returns."""
        self.session.add(token)

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

    async def delete_expired(self, older_than_days: int = 7) -> int:
        """
        Deletes tokens that expired more than `older_than_days` ago.
        Intended to be called periodically (e.g. daily) to prevent auth_tokens
        table bloat. Returns the number of rows deleted.

        Safe to run at any time — only targets tokens past their expiry window.
        A 7-day grace period retains tokens for forensic/audit review before purge.
        """
        cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
        result = await self.session.execute(
            delete(AuthToken).where(AuthToken.expires_at < cutoff)
        )
        return int(result.rowcount)  # type: ignore[attr-defined]

    async def delete_for_email(self, email: str) -> None:
        """Hard-deletes all tokens for an email address. Used by GDPR erasure."""
        await self.session.execute(delete(AuthToken).where(AuthToken.email == email))
