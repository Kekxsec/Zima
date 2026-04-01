# backend/app/core/startup.py
from backend.app.core.config import settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

REQUIRED_IN_PRODUCTION = [
    ("resend_api_key", "Email delivery will not work"),
    ("stripe_secret_key", "Billing will not work"),
    ("stripe_webhook_secret", "Webhooks will not work"),
    ("hibp_api_key", "Breach monitoring will not work"),
]


def check_environment() -> None:
    if not settings.is_production:
        return  # Only enforce in production

    warnings = []
    for attr, message in REQUIRED_IN_PRODUCTION:
        if not getattr(settings, attr, None):
            warnings.append(f"Missing {attr.upper()}: {message}")

    if warnings:
        for w in warnings:
            logger.warning("startup.missing_config", message=w)
        # In production, fail hard if critical config is missing
        raise RuntimeError(
            "Missing required production configuration:\n" + "\n".join(warnings)
        )


async def check_redis() -> None:
    """
    Verify Redis is reachable before accepting traffic.

    Rate limiting (slowapi) uses Redis for shared counter storage.  If Redis
    is unavailable the limiter fails-open — every request is allowed through,
    removing OTP brute-force and DDoS protection.  We prefer a hard failure
    at startup over a silently unprotected deployment.
    """
    import redis.asyncio as aioredis

    try:
        client: aioredis.Redis = aioredis.from_url(
            settings.redis_url, socket_connect_timeout=3
        )
        await client.ping()
        await client.aclose()
        logger.info("startup.redis_ok")
    except Exception as exc:
        logger.error("startup.redis_unavailable", error=str(exc))
        raise RuntimeError(
            f"Redis is not reachable at startup ({exc}). "
            "Rate limiting would fail-open. Aborting to protect OTP and scan "
            "endpoints."
        ) from exc
