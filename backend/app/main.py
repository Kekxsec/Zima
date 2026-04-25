# backend/app/main.py
import asyncio
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import secure
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.app.api.router import api_router
from backend.app.core.config import settings
from backend.app.core.logging import configure_logging, get_logger
from backend.app.core.rate_limit import limiter
from backend.app.core.startup import (
    check_environment,
    check_redis,
    check_tls_in_connection_strings,
    seed_service_registry,
)

logger = get_logger(__name__)

_CLEANUP_INTERVAL_SECONDS = 24 * 60 * 60  # 24 hours
_REDIS_HEALTH_CHECK_INTERVAL = 60  # seconds
_DEFAULT_MAX_REQUEST_BODY_BYTES = 10 * 1024 * 1024  # 10 MB — matches vault import cap
_MAILBOX_UPLOAD_MAX_REQUEST_BODY_BYTES = settings.mailbox_upload_max_mb * 1024 * 1024

# Methods that mutate state — subject to CSRF / Origin enforcement.
_STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

# Paths exempt from CSRF Origin enforcement. These either:
#   - use Bearer auth only (companion / extension), so SameSite cookies don't apply, or
#   - are unauthenticated public endpoints.
_CSRF_EXEMPT_PREFIXES = (
    "/api/v1/companion/",
    "/api/v1/extension/",
    "/api/v1/billing/webhook",  # signed by Stripe, not browser-driven
    "/health",
)


def _max_request_body_bytes_for_path(path: str) -> int:
    """
    Return the request-body cap for a given route path.

    Mailbox uploads are intentionally larger than vault imports because Proton
    Mail folder exports can contain thousands of `.eml` files.
    """
    if path.startswith("/api/v1/email-accounts/uploads"):
        return _MAILBOX_UPLOAD_MAX_REQUEST_BODY_BYTES
    return _DEFAULT_MAX_REQUEST_BODY_BYTES


async def _periodic_redis_health_check() -> None:
    """
    Periodically verify Redis is still reachable.

    slowapi fails-open when Redis is unavailable: all requests are allowed
    through, silently removing OTP brute-force and scan-rate protection.
    This task logs an error every 60 seconds while Redis is down so the
    outage is visible in production monitoring and can trigger an alert.
    """
    import redis.asyncio as aioredis

    while True:
        try:
            await asyncio.sleep(_REDIS_HEALTH_CHECK_INTERVAL)
            client: aioredis.Redis = aioredis.from_url(
                settings.redis_url, socket_connect_timeout=3
            )
            await client.ping()  # type: ignore[misc]
            await client.aclose()
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error(
                "security.redis_health_check_failed",
                error=str(exc),
                detail=(
                    "Rate limiting is likely fail-open. "
                    "OTP brute-force protection may be inactive."
                ),
            )


async def _periodic_token_cleanup() -> None:
    """
    Deletes expired auth_tokens rows older than 7 days.
    Runs on a 24-hour cycle for the lifetime of the process.
    Creates its own DB session per Rule 3 (background tasks must not reuse
    request-scoped sessions).
    """
    while True:
        try:
            await asyncio.sleep(_CLEANUP_INTERVAL_SECONDS)
            from backend.app.db.repositories.auth_tokens import AuthTokenRepository
            from backend.app.db.session import AsyncSessionLocal

            async with AsyncSessionLocal() as session:
                repo = AuthTokenRepository(session)
                deleted = await repo.delete_expired()
                await session.commit()
            logger.info("auth.tokens.cleanup_complete", deleted=deleted)
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("auth.tokens.cleanup_failed", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    check_environment()
    check_tls_in_connection_strings()
    await check_redis()

    # Clear stale scans from any previous crashed instance
    from backend.app.db.repositories.scans import ScanRepository
    from backend.app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        scan_repo = ScanRepository(session)
        stale_count = await scan_repo.mark_stale_scans_failed()
        await session.commit()
        if stale_count > 0:
            logger.info("startup.stale_scans_cleared", count=stale_count)

    # Ensure the built-in service registry is populated (idempotent upsert)
    await seed_service_registry()

    # Re-run any GDPR erasure tasks that were interrupted by a server restart
    from backend.app.jobs.recovery import recover_stale_deletions

    await recover_stale_deletions()

    cleanup_task = asyncio.create_task(_periodic_token_cleanup())
    redis_health_task = asyncio.create_task(_periodic_redis_health_check())
    try:
        yield
    finally:
        for task in (cleanup_task, redis_health_task):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


secure_headers = secure.Secure(
    hsts=secure.StrictTransportSecurity().max_age(31536000).include_subdomains(),
    xfo=secure.XFrameOptions().deny(),
    csp=secure.ContentSecurityPolicy()
    .default_src("'self'")
    .script_src("'self'")
    .style_src("'self'")
    .img_src("'self'", "data:")
    .connect_src("'self'"),
    referrer=secure.ReferrerPolicy().strict_origin_when_cross_origin(),
    cache=secure.CacheControl().no_store(),
    xcto=secure.XContentTypeOptions(),
    permissions=secure.PermissionsPolicy().geolocation().camera().microphone(),
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Zima API",
        version="0.1.0",
        lifespan=lifespan,
        redirect_slashes=False,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    @app.exception_handler(Exception)
    async def global_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "unhandled_exception",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            exc_type=type(exc).__name__,
            exc_info=not settings.is_production,
        )
        if settings.is_production:
            return JSONResponse(
                status_code=500,
                content={"detail": "An internal error occurred."},
            )
        return JSONResponse(
            status_code=500,
            content={"detail": str(exc)},
        )

    @app.middleware("http")
    async def enforce_max_body_size(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        Fast-reject oversized requests before they reach endpoint handlers.
        Relies on the Content-Length header for early rejection; requests that
        omit Content-Length are still bounded by the chunked reader in each
        endpoint (e.g. _read_upload_limited in imports.py).
        """
        if request.method in ("POST", "PUT", "PATCH"):
            content_length_header = request.headers.get("content-length")
            if content_length_header:
                try:
                    max_bytes = _max_request_body_bytes_for_path(request.url.path)
                    if int(content_length_header) > max_bytes:
                        return JSONResponse(
                            status_code=413,
                            content={
                                "detail": (
                                    f"Request body too large. Maximum allowed size is "
                                    f"{max_bytes // (1024 * 1024)} MB."
                                )
                            },
                        )
                except ValueError:
                    pass
        return await call_next(request)

    @app.middleware("http")
    async def enforce_csrf_origin(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """
        Defence-in-depth CSRF protection for cookie-authenticated, state-changing
        requests. Bearer-authenticated callers (companion/extension/API clients)
        are exempt because cookie SameSite policy does not apply to them.

        Strategy: when the request mutates state and does NOT carry a Bearer
        token, require Origin (or Referer) to match the configured allow-list.
        Browsers always send Origin on cross-origin POST, so a missing/foreign
        Origin is a strong forgery signal.
        """
        if request.method not in _STATE_CHANGING_METHODS:
            return await call_next(request)

        # The TestClient cannot supply a meaningful Origin header. Skip the
        # check in the testing environment; production / development still
        # enforce because real browsers always send Origin on POST.
        if settings.is_testing:
            return await call_next(request)

        path = request.url.path
        if any(path.startswith(p) for p in _CSRF_EXEMPT_PREFIXES):
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            return await call_next(request)

        allowed_origins = set(settings.cors_allowed_origins)
        origin = request.headers.get("origin")
        referer = request.headers.get("referer")

        def _origin_allowed(value: str | None) -> bool:
            if not value:
                return False
            for allowed in allowed_origins:
                if value == allowed or value.startswith(f"{allowed}/"):
                    return True
            return False

        if not (_origin_allowed(origin) or _origin_allowed(referer)):
            logger.warning(
                "security.csrf_origin_rejected",
                path=path,
                method=request.method,
                origin=origin,
                referer=referer,
            )
            return JSONResponse(
                status_code=403,
                content={"detail": "Origin not allowed for this request."},
            )

        return await call_next(request)

    @app.middleware("http")
    async def set_security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        secure_headers.set_headers(response)  # type: ignore[arg-type]
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(api_router)

    return app


app = create_app()
