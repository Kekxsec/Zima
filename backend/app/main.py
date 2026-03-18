# backend/app/main.py
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import secure
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from backend.app.api.router import api_router
from backend.app.core.config import settings
from backend.app.core.logging import configure_logging
from backend.app.core.rate_limit import limiter


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    yield


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
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Zima API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]  # slowapi typing

    @app.middleware("http")
    async def set_security_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        response = await call_next(request)
        secure_headers.set_headers(response)  # type: ignore[arg-type]  # secure library MutableHeaders compat
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(api_router)

    return app


app = create_app()
