# backend/app/providers/base/quota.py
"""
Per-user, per-provider daily API call quota enforcement.

Uses Redis atomic INCR + EXPIRE to track call counts with a rolling 24-hour
window scoped to UTC calendar days. Fails open on Redis errors so a Redis
outage does not block scans — the separate Redis health check at startup
handles alerting on connectivity loss.

Only providers with per-query costs need quota enforcement here. Providers
that have their own server-side rate limiting (HIBP) are excluded.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Final

from backend.app.core.config import settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

# Conservative daily per-user limits. Increase after establishing cost baselines.
_DEFAULT_DAILY_QUOTA: Final[dict[str, int]] = {
    "dehashed": 50,
    "breachdirectory": 25,
    "hudson_rock": 25,
    "leakcheck": 50,
}

_REDIS_KEY_PREFIX = "zima:pquota"
_TTL_SECONDS = 86_400  # 24 hours


class ProviderQuotaGuard:
    """
    Check and increment per-user/per-provider daily call counts via Redis.

    Usage::

        guard = ProviderQuotaGuard()
        if not await guard.check_and_increment(user_id, "dehashed"):
            logger.warning("quota_exceeded", provider="dehashed")
            return []  # skip provider
        # safe to call provider

    Providers not listed in the quota table are always allowed through.
    Fails open (returns True) when Redis is unreachable.
    """

    def __init__(self, daily_limits: dict[str, int] | None = None) -> None:
        self._limits: dict[str, int] = daily_limits or dict(_DEFAULT_DAILY_QUOTA)

    def _key(self, user_id: uuid.UUID, provider: str) -> str:
        date_str = datetime.now(UTC).strftime("%Y-%m-%d")
        return f"{_REDIS_KEY_PREFIX}:{user_id}:{provider}:{date_str}"

    async def check_and_increment(self, user_id: uuid.UUID, provider: str) -> bool:
        """
        Return True if this provider call is within the user's daily quota and
        record the call. Return False if the quota is exhausted.

        Uses INCR so the count is updated atomically. If count reaches 1 (first
        call today) the TTL is set so stale keys self-expire.

        Fails open on Redis errors — a Redis outage allows calls through rather
        than blocking scans. Redis health is enforced separately at startup.
        """
        limit = self._limits.get(provider)
        if limit is None:
            return True  # Provider has no defined quota; always allow

        import redis.asyncio as aioredis

        try:
            client: aioredis.Redis = aioredis.from_url(
                settings.redis_url, socket_connect_timeout=2
            )
            key = self._key(user_id, provider)
            current: int = await client.incr(key)
            if current == 1:
                # First call today — attach expiry so key cleans itself up
                await client.expire(key, _TTL_SECONDS)
            await client.aclose()
        except Exception as exc:
            logger.warning(
                "quota_guard.redis_error",
                provider=provider,
                user_id=str(user_id),
                error=str(exc),
            )
            return True  # Fail open

        if current > limit:
            logger.warning(
                "quota_guard.quota_exceeded",
                provider=provider,
                user_id=str(user_id),
                count=current,
                limit=limit,
            )
            return False

        return True
