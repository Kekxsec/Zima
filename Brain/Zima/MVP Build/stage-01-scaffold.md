← [[MVP Master|Stage Progress]]

# Stage 1 — Scaffold

**Exit condition:** Full folder structure in place. `core/` fully implemented. Database migrations run cleanly. Security headers and CORS load from environment. Health and readiness endpoints return 200. Import checker passes. CI is green.

---

## 1.1 Full Folder Structure

Create every directory and an `__init__.py` in each. Stub files first — implementations follow in later stages.

```text
zima/
├── backend/
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── router.py
│       │   ├── dependencies.py
│       │   └── v1/
│       │       ├── __init__.py
│       │       ├── health.py
│       │       ├── auth.py
│       │       ├── onboarding.py
│       │       ├── scans.py
│       │       ├── findings.py
│       │       ├── assets.py
│       │       ├── scores.py
│       │       └── account.py        ← GDPR deletion, data export
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── logging.py
│       │   ├── exceptions.py
│       │   ├── enums.py
│       │   └── utils.py
│       ├── db/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── session.py
│       │   ├── models/
│       │   │   ├── __init__.py           ← Empty — create this file
│       │   │   └── audit.py              ← Created in Stage 1b — stub only here
│       │   └── repositories/
│       │       ├── __init__.py
│       │       ├── users.py
│       │       ├── auth_tokens.py
│       │       ├── assets.py
│       │       ├── signals.py
│       │       ├── findings.py
│       │       ├── scores.py
│       │       ├── scans.py              ← Scan history
│       │       └── audit.py
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── models.py             ← User + AuthToken (no passwords)
│       │   ├── service.py
│       │   ├── schemas.py
│       │   └── utils.py
│       ├── assets/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── schemas.py
│       │   ├── service.py
│       │   └── graph.py
│       ├── signals/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── schemas.py
│       │   ├── normalizer.py
│       │   ├── registry.py
│       │   └── dedup.py
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base/
│       │   │   ├── __init__.py
│       │   │   ├── client.py
│       │   │   ├── models.py
│       │   │   ├── exceptions.py
│       │   │   ├── auth.py
│       │   │   └── rate_limit.py
│       │   └── breach/
│       │       └── hibp/
│       │           ├── __init__.py
│       │           ├── client.py
│       │           ├── auth.py
│       │           ├── schemas.py
│       │           ├── mapper.py
│       │           ├── config.py
│       │           ├── rate_limit.py
│       │           ├── exceptions.py
│       │           └── tests/
│       ├── modules/
│       │   ├── __init__.py
│       │   ├── base/
│       │   │   ├── __init__.py
│       │   │   └── service.py
│       │   └── identity/
│       │       └── breach_monitor/
│       │           ├── __init__.py
│       │           ├── service.py
│       │           ├── mapper.py
│       │           ├── rules.py
│       │           ├── schemas.py
│       │           ├── config.py
│       │           ├── constants.py
│       │           ├── README.md
│       │           └── tests/
│       ├── correlation/
│       │   ├── __init__.py
│       │   ├── engine.py
│       │   ├── findings.py
│       │   ├── models.py
│       │   └── rules/
│       │       ├── __init__.py
│       │       └── identity_compromise.py
│       ├── scoring/
│       │   ├── __init__.py
│       │   ├── engine.py
│       │   ├── models.py
│       │   ├── weights.py
│       │   ├── policies.py
│       │   └── calculators/
│       │       ├── __init__.py
│       │       └── identity_score.py
│       ├── remediation/
│       │   ├── __init__.py
│       │   ├── engine.py
│       │   ├── templates.py
│       │   ├── models.py
│       │   ├── playbooks/
│       │   │   └── rotate_credentials.md
│       │   └── tests/
│       ├── automation/
│       │   ├── __init__.py
│       │   ├── engine.py
│       │   ├── approvals.py
│       │   ├── audit.py
│       │   └── workflows/
│       │       └── __init__.py
│       ├── billing/
│       │   ├── __init__.py
│       │   ├── service.py
│       │   ├── webhooks.py
│       │   └── schemas.py
│       ├── email/
│       │   ├── __init__.py
│       │   ├── service.py
│       │   └── templates/
│       │       ├── otp.py
│       │       └── breach_alert.py
│       ├── tiers/
│       │   ├── __init__.py
│       │   ├── loader.py
│       │   ├── checker.py
│       │   └── config/
│       │       ├── core.yaml
│       │       ├── plus.yaml
│       │       ├── pro.yaml
│       │       └── business.yaml
│       └── jobs/
│           ├── __init__.py
│           ├── runner.py
│           ├── orchestrator.py
│           └── alerts.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── fixtures/
├── scripts/
│   └── check_imports.py
├── docs/
├── infra/
│   └── nginx/
│       └── nginx.conf
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml
├── CLAUDE.md
└── README.md
```

---

## 1.2 Core Layer

### config.py

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr
from typing import Literal

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_env: Literal["development", "testing", "production"] = "development"
    debug: bool = False
    secret_key: SecretStr

    # Database
    database_url: str
    database_url_sync: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # CORS — loaded from environment, never hardcoded
    cors_allowed_origins: list[str] = ["http://localhost:3000"]

    # Email
    resend_api_key: SecretStr | None = None
    email_from_address: str = "noreply@yourdomain.com"
    email_from_name: str = "Zima"

    # Stripe
    stripe_secret_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    stripe_price_shield_monthly: str | None = None
    stripe_price_pro_monthly: str | None = None

    # Providers
    hibp_api_key: SecretStr | None = None

    # Tier
    default_tier: str = "core"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        return self.app_env == "testing"


settings = Settings()
```

### enums.py

```python
from enum import StrEnum

class Severity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class Confidence(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class SignalStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    STALE = "stale"

class FindingStatus(StrEnum):
    OPEN = "open"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"

class Tier(StrEnum):
    CORE = "core"
    PLUS = "plus"
    PRO = "pro"
    BUSINESS = "business"

class EntityType(StrEnum):
    EMAIL = "email"
    USERNAME = "username"
    DOMAIN = "domain"
    ACCOUNT = "account"
    DEVICE = "device"
    PHONE_NUMBER = "phone_number"
    IP = "ip"
    URL = "url"

class ScanStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
```

### exceptions.py

```python
class ZimaBaseException(Exception):
    def __init__(self, message: str, code: str | None = None) -> None:
        self.message = message
        self.code = code
        super().__init__(message)

class ProviderException(ZimaBaseException): pass
class ProviderAuthException(ProviderException): pass
class ProviderRateLimitException(ProviderException): pass
class ProviderTimeoutException(ProviderException): pass
class ModuleException(ZimaBaseException): pass
class SignalValidationException(ZimaBaseException): pass
class TierPermissionException(ZimaBaseException): pass
class EntityNotFoundException(ZimaBaseException): pass

# Auth
class AuthTokenInvalidException(ZimaBaseException): pass
class AuthTokenExpiredException(ZimaBaseException): pass
class AuthTokenAlreadyUsedException(ZimaBaseException): pass
class AuthOTPRateLimitException(ZimaBaseException): pass

# GDPR
class UserDeletionException(ZimaBaseException): pass
```

---

## 1.3 Database Layer

### db/base.py

```python
from datetime import datetime, timezone
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
```

### db/session.py

```python
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession, async_sessionmaker, create_async_engine
)
from backend.app.core.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

`AsyncSessionLocal` is exported directly so background tasks can create their own sessions:

```python
# Pattern for every background task — never pass a request-scoped session
async def my_background_task(user_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as session:
        repo = MyRepository(session)
        await repo.do_work()
```

---

## 1.4 Scan History Model

The `Scan` model records every scan execution. Without this, there is no way to surface scan history to users, debug failures, or show score trends over time.

```python
# db/repositories/scans.py (model section)
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, JSON, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.db.base import Base, TimestampMixin
from backend.app.core.enums import ScanStatus

class Scan(Base, TimestampMixin):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(
        String(20), default=ScanStatus.PENDING, nullable=False, index=True
    )
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    signals_created: Mapped[int] = mapped_column(Integer, default=0)
    findings_created: Mapped[int] = mapped_column(Integer, default=0)
    domains_run: Mapped[list] = mapped_column(JSON, default=list)
    error_detail: Mapped[str | None] = mapped_column(String(1024), nullable=True)
```

---

## 1.5 Security Headers Middleware

This must be configured before the app is usable. Do not leave this for later.

```python
# main.py
import secure
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from contextlib import asynccontextmanager
from backend.app.core.config import settings
from backend.app.core.logging import configure_logging
from backend.app.api.router import api_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield

limiter = Limiter(key_func=get_remote_address)

# Security headers policy
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
    xxp=secure.XXSSProtection().set("0"),  # Modern browsers — disable legacy XSS filter
    content=secure.XContentTypeOptions(),
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Zima API",
        version="0.1.0",
        lifespan=lifespan,
        # Hide docs in production
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
        openapi_url="/openapi.json" if not settings.is_production else None,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # Security headers on every response
    @app.middleware("http")
    async def set_security_headers(request: Request, call_next) -> Response:
        response = await call_next(request)
        secure_headers.framework.fastapi(response)
        return response

    # CORS — origins loaded from environment, never hardcoded
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
```

---

## 1.6 HTTPS — Nginx Configuration

HTTPS is enforced at the Nginx reverse proxy layer. The application itself runs on HTTP internally; Nginx handles TLS termination. Create this config now even if you're not deploying yet — it documents the intention and prevents accidentally running without TLS.

```nginx
# infra/nginx/nginx.conf
server {
    listen 80;
    server_name yourdomain.com;

    # Redirect all HTTP to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate     /etc/ssl/certs/yourdomain.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.key;

    # Modern TLS only
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # HSTS — also set in application headers for defence in depth
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }
}
```

Use Let's Encrypt with Certbot for the certificate in production. For local development, HTTPS is not required — the security headers middleware still loads and is tested.

---

## 1.7 Health Endpoints

```python
# api/v1/health.py
from fastapi import APIRouter
from sqlalchemy import text
from backend.app.db.session import AsyncSessionLocal

router = APIRouter(tags=["health"])

@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}

@router.get("/health/ready")
async def readiness() -> dict:
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ready", "database": "ok"}
```

---

## 1.8 Tier Configuration Files

```yaml
# tiers/config/core.yaml
enabled_domains:
  - identity
  - accounts
  - device
  - browser
```

```yaml
# tiers/config/plus.yaml
enabled_domains:
  - identity
  - accounts
  - device
  - browser
  - network
  - privacy
  - darkweb
  - backup
  - threat_intel
```

```yaml
# tiers/config/pro.yaml
enabled_domains:
  - identity
  - accounts
  - device
  - browser
  - network
  - privacy
  - darkweb
  - backup
  - threat_intel
  - domain
  - email
  - infrastructure
  - secrets
  - supply_chain
```

```yaml
# tiers/config/business.yaml
enabled_domains:
  - identity
  - accounts
  - device
  - browser
  - network
  - privacy
  - darkweb
  - backup
  - threat_intel
  - domain
  - email
  - infrastructure
  - secrets
  - supply_chain
  - cloud
  - saas
  - incident_readiness
  - compliance
```

```python
# tiers/loader.py
from pathlib import Path
from functools import lru_cache
import yaml
from backend.app.core.enums import Tier

TIER_CONFIG_DIR = Path(__file__).parent / "config"

@lru_cache(maxsize=None)
def load_tier_config(tier: Tier) -> dict:
    path = TIER_CONFIG_DIR / f"{tier.value}.yaml"
    with path.open() as f:
        return yaml.safe_load(f)

def get_enabled_domains(tier: Tier) -> list[str]:
    return load_tier_config(tier).get("enabled_domains", [])

def is_domain_enabled(domain: str, tier: Tier) -> bool:
    return domain in get_enabled_domains(tier)
```

**Note:** The `lru_cache` means tier config changes require an app restart. This is acceptable for MVP. When Stripe billing is integrated and tier upgrades need to take effect immediately, invalidate the cache after processing the webhook: `load_tier_config.cache_clear()`.
