# backend/app/core/rate_limit.py
from fastapi import Request
from slowapi import Limiter

from backend.app.auth.utils import decode_access_token
from backend.app.core.config import settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

_SESSION_COOKIE_NAME = "zima_session"


def get_real_ip(request: Request) -> str:
    """
    Extract the real client IP from the request.

    Railway (and most reverse-proxy deployments) sets X-Forwarded-For to a
    comma-separated chain: "<client>, <proxy1>, <proxy2>". The leftmost entry
    is the original client IP. X-Real-IP is set by nginx as a single value.

    SECURITY NOTE: X-Forwarded-For can be spoofed if the app is reachable
    directly (without going through the proxy). On Railway, all traffic is
    routed through the Railway load balancer, so the first XFF value is
    authoritative. If this changes (e.g. direct TCP exposure), configure a
    trusted-proxy allowlist and take the rightmost non-trusted IP instead.
    """
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    return request.client.host if request.client else "unknown"


def get_rate_limit_key(request: Request) -> str:
    """
    Prefer an authenticated user key when a valid session is present.

    This keeps authenticated rate limits scoped per user rather than per IP,
    which matters in local development and behind shared proxies.
    """
    token = request.cookies.get(_SESSION_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if token:
        try:
            payload = decode_access_token(token)
        except ValueError:
            logger.warning("rate_limit.invalid_token", reason="token decode failed")
            return f"ip:{get_real_ip(request)}"
        else:
            subject = payload.get("sub")
            if isinstance(subject, str) and subject:
                return f"user:{subject}"

    return f"ip:{get_real_ip(request)}"


# Redis-backed storage so rate limit counters are:
#   - Shared across all worker processes (multi-worker correctness)
#   - Persistent across restarts (no counter reset on deploy)
#
# FAIL-OPEN WARNING: if Redis becomes transiently unavailable after startup,
# slowapi allows requests through rather than blocking them. Monitor Redis
# health and alert on connection failures to avoid unprotected OTP windows.
# At startup, a Redis connection failure raises immediately (fail-closed).
limiter = Limiter(key_func=get_rate_limit_key, storage_uri=settings.redis_url)
