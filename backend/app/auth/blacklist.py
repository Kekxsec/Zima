# backend/app/auth/blacklist.py
"""
Redis-backed JWT revocation list.

Tokens are identified by their `jti` claim (UUID4 per token).
On logout the JTI is written to Redis with a TTL equal to the token's
remaining lifetime, so entries expire automatically and the set never grows
unbounded.

Fail-open on Redis errors: if Redis is unavailable the check returns False
and the timestamp-based session_revoked_at fallback in get_current_user
continues to protect sessions.  A log.error is emitted so the outage is
visible in production monitoring.
"""

from datetime import UTC, datetime

import redis.asyncio as aioredis

from backend.app.core.config import settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

_BLACKLIST_PREFIX = "jwt:revoked:"


class TokenBlacklist:
    """Thin wrapper around a Redis key-per-JTI revocation store."""

    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None  # type: ignore[type-arg]

    def _client(self) -> aioredis.Redis:  # type: ignore[type-arg]
        if self._redis is None:
            self._redis = aioredis.from_url(
                settings.redis_url, socket_connect_timeout=3
            )
        return self._redis

    async def revoke(self, jti: str, expires_at: datetime) -> None:
        """
        Mark a JTI as revoked until its natural expiry.
        No-op if the token is already expired.
        """
        ttl = int((expires_at - datetime.now(UTC)).total_seconds())
        if ttl <= 0:
            return
        try:
            await self._client().setex(f"{_BLACKLIST_PREFIX}{jti}", ttl, "1")
        except Exception as exc:
            logger.error("security.blacklist.revoke_failed", jti=jti, error=str(exc))

    async def is_revoked(self, jti: str) -> bool:
        """
        Returns True if the JTI is in the revocation list.
        Returns False on Redis error (fail-open) and emits a log.error.
        """
        try:
            result = await self._client().get(f"{_BLACKLIST_PREFIX}{jti}")
            return result is not None
        except Exception as exc:
            logger.error(
                "security.blacklist.check_failed",
                jti=jti,
                error=str(exc),
                detail="Falling back to timestamp-based revocation check.",
            )
            return False


# Module-level singleton — Redis connection is lazy and shared across requests.
token_blacklist = TokenBlacklist()
