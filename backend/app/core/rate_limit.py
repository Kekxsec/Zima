# backend/app/core/rate_limit.py
from fastapi import Request
from slowapi import Limiter

from backend.app.core.config import settings


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


# Redis-backed storage so rate limit counters are:
#   - Shared across all worker processes (multi-worker correctness)
#   - Persistent across restarts (no counter reset on deploy)
#
# FAIL-OPEN WARNING: if Redis becomes transiently unavailable after startup,
# slowapi allows requests through rather than blocking them. Monitor Redis
# health and alert on connection failures to avoid unprotected OTP windows.
# At startup, a Redis connection failure raises immediately (fail-closed).
limiter = Limiter(key_func=get_real_ip, storage_uri=settings.redis_url)
