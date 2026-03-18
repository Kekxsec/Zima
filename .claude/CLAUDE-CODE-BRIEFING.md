# ZIMA — CLAUDE CODE MASTER BRIEFING

**Read this entire document before reading any stage file. This document is the authoritative reference for every decision not covered explicitly in a stage file. When in doubt, return here.**

---

## HOW TO USE THESE STAGE FILES

Each stage file is a precise specification. Follow these rules exactly:

1. **Create every file listed before moving to the next section within a stage.** The order within each stage matters. Do not skip files.
2. **Every code block contains the complete content of that file unless explicitly marked as an addition.** Do not merge, abbreviate, or reinterpret.
3. **Every file path comment at the top of a code block (`# path/to/file.py`) is the exact location in the repository.** Relative to the repo root.
4. **When a code block is marked `# ADDITION TO: path/to/file.py`, append it to the existing file.** Do not replace the file.
5. **Do not invent imports.** Every import in every file must be from a package in `pyproject.toml` or from within the `backend/` package. If an import does not exist yet, stop and flag it.
6. **Do not add functionality not in the spec.** If a function or endpoint is not described, do not create it.
7. **Run the verification command at the end of each stage before proceeding to the next.**

---

## REPOSITORY STRUCTURE — CANONICAL

Every file lives at exactly this path. No exceptions.

```
zima/
├── backend/
│   └── app/
│       ├── __init__.py
│       ├── main.py
│       ├── api/
│       │   ├── __init__.py
│       │   ├── router.py                   ← Registers all v1 sub-routers
│       │   ├── dependencies.py             ← get_current_user, get_db_session, get_auth_service, get_asset_service
│       │   └── v1/
│       │       ├── __init__.py
│       │       ├── health.py
│       │       ├── auth.py
│       │       ├── onboarding.py
│       │       ├── scans.py
│       │       ├── findings.py
│       │       ├── signals.py
│       │       ├── scores.py
│       │       ├── account.py
│       │       ├── billing.py
│       │       └── legal.py
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py
│       │   ├── logging.py
│       │   ├── exceptions.py
│       │   ├── enums.py
│       │   ├── schemas.py                  ← Shared PaginationParams schema
│       │   └── utils.py
│       ├── db/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── session.py
│       │   ├── models/
│       │   │   ├── __init__.py
│       │   │   └── audit.py                ← AuditEvent model ONLY — create in Stage 1b
│       │   └── repositories/
│       │       ├── __init__.py
│       │       ├── users.py                ← UserRepository — MUST be created in Stage 2
│       │       ├── auth_tokens.py
│       │       ├── assets.py               ← AssetRepository — MUST be created in Stage 3
│       │       ├── signals.py
│       │       ├── findings.py
│       │       ├── scores.py
│       │       ├── scans.py
│       │       └── audit.py
│       ├── auth/
│       │   ├── __init__.py
│       │   ├── models.py                   ← User + AuthToken ONLY. No Scan model here.
│       │   ├── service.py
│       │   ├── schemas.py
│       │   └── utils.py
│       ├── assets/
│       │   ├── __init__.py
│       │   ├── models.py                   ← Asset model
│       │   ├── schemas.py
│       │   └── service.py                  ← AssetService with register_verified_email
│       ├── signals/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   ├── schemas.py
│       │   └── dedup.py
│       ├── providers/
│       │   ├── __init__.py
│       │   ├── base/
│       │   │   ├── __init__.py
│       │   │   ├── client.py
│       │   │   └── exceptions.py
│       │   └── breach/
│       │       └── hibp/
│       │           ├── __init__.py
│       │           ├── client.py
│       │           ├── schemas.py
│       │           ├── mapper.py
│       │           └── exceptions.py
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
│       │           └── constants.py
│       ├── correlation/
│       │   ├── __init__.py
│       │   ├── engine.py
│       │   ├── models.py
│       │   └── rules/
│       │       ├── __init__.py
│       │       └── identity_compromise.py
│       ├── scoring/
│       │   ├── __init__.py
│       │   ├── models.py
│       │   └── calculators/
│       │       ├── __init__.py
│       │       └── identity_score.py
│       ├── remediation/
│       │   ├── __init__.py
│       │   └── engine.py
│       ├── automation/
│       │   ├── __init__.py
│       │   └── engine.py                   ← Stub only in MVP
│       ├── billing/
│       │   ├── __init__.py
│       │   ├── service.py
│       │   └── webhooks.py
│       ├── email/
│       │   ├── __init__.py
│       │   ├── service.py
│       │   └── templates/
│       │       ├── __init__.py
│       │       ├── otp.py
│       │       └── breach_alert.py
│       ├── tiers/
│       │   ├── __init__.py
│       │   ├── loader.py
│       │   └── config/
│       │       ├── core.yaml
│       │       ├── plus.yaml
│       │       ├── pro.yaml
│       │       └── business.yaml
│       └── jobs/
│           ├── __init__.py
│           ├── runner.py
│           └── orchestrator.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── factories.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── auth/
│   │   │   └── __init__.py
│   │   ├── signals/
│   │   │   └── __init__.py
│   │   ├── modules/
│   │   │   └── __init__.py
│   │   ├── correlation/
│   │   │   └── __init__.py
│   │   └── scoring/
│   │       └── __init__.py
│   ├── integration/
│   │   └── __init__.py
│   └── api/
│       └── __init__.py
├── scripts/
│   └── check_imports.py
├── docs/
├── infra/
│   └── nginx/
│       └── nginx.conf
├── .github/
│   └── workflows/
│       └── ci.yml
├── docker-compose.yml
├── Dockerfile
├── railway.toml
├── pyproject.toml
├── alembic.ini
├── .env
├── .env.example
├── .gitignore
├── .python-version
├── .pre-commit-config.yaml
├── CLAUDE.md
└── README.md
```

---

## CANONICAL IMPLEMENTATIONS — REFERENCE THESE WHEN A STAGE FILE SAYS "defined earlier"

### db/repositories/users.py — Complete Implementation

```python
# backend/app/db/repositories/users.py
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.auth.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: str | uuid.UUID) -> User | None:
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.stripe_customer_id == email)
        )
        # Note: User table does not have an email column.
        # Email lives in the Asset table (entity_type='email', is_primary=True).
        # Use AssetRepository.get_primary_email_for_user() to find the user by email.
        # This method exists only for the auth flow where we have the email and
        # need the associated user. Use the join query below.
        result = await self.session.execute(
            select(User)
            .join(
                __import__("backend.app.assets.models", fromlist=["Asset"]).Asset,
                __import__("backend.app.assets.models", fromlist=["Asset"]).Asset.user_id == User.id,
            )
            .where(
                __import__("backend.app.assets.models", fromlist=["Asset"]).Asset.entity_type == "email",
                __import__("backend.app.assets.models", fromlist=["Asset"]).Asset.value == email,
                __import__("backend.app.assets.models", fromlist=["Asset"]).Asset.is_primary == True,  # noqa: E712
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_active_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.session.execute(
            select(User).where(
                User.id == user_id,
                User.is_active == True,  # noqa: E712
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
```

**IMPORTANT NOTE on UserRepository.get_by_email:** The User model has no email column. Email is stored in the Asset table. The auth flow creates/looks up users differently — see the exact implementation in stage-02-otp-auth.md section 2.3. The `get_by_email` join above is the correct pattern.

### db/repositories/assets.py — Complete Implementation

```python
# backend/app/db/repositories/assets.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.assets.models import Asset


class AssetRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_value(
        self,
        user_id: uuid.UUID,
        entity_type: str,
        value: str,
    ) -> Asset | None:
        result = await self.session.execute(
            select(Asset).where(
                Asset.user_id == user_id,
                Asset.entity_type == entity_type,
                Asset.value == value,
            )
        )
        return result.scalar_one_or_none()

    async def get_verified_for_user(
        self,
        user_id: uuid.UUID,
        entity_type: str,
    ) -> list[Asset]:
        """Returns only verified assets. Used by module runner — unverified assets must not be scanned."""
        result = await self.session.execute(
            select(Asset).where(
                Asset.user_id == user_id,
                Asset.entity_type == entity_type,
                Asset.is_verified == True,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def get_all_for_user(self, user_id: uuid.UUID) -> list[Asset]:
        result = await self.session.execute(
            select(Asset).where(Asset.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_primary_email(self, user_id: uuid.UUID) -> Asset | None:
        """Returns the primary email asset for notification purposes."""
        result = await self.session.execute(
            select(Asset).where(
                Asset.user_id == user_id,
                Asset.entity_type == "email",
                Asset.is_primary == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()
```

### api/dependencies.py — Complete Implementation

```python
# backend/app/api/dependencies.py
from collections.abc import AsyncGenerator
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.assets.service import AssetService
from backend.app.auth.models import User
from backend.app.auth.service import AuthService
from backend.app.auth.utils import decode_access_token
from backend.app.db.repositories.assets import AssetRepository
from backend.app.db.repositories.auth_tokens import AuthTokenRepository
from backend.app.db.repositories.users import UserRepository
from backend.app.db.session import get_db_session  # Re-exported from here for consistency

# All endpoint files import BOTH get_current_user and get_db_session from this module:
#   from backend.app.api.dependencies import get_current_user, get_db_session
# This is the canonical import path for both dependency functions.

__all__ = ["get_current_user", "get_auth_service", "get_asset_service", "get_db_session"]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/otp/verify")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
    except ValueError:
        raise credentials_exception

    user_repo = UserRepository(db)
    try:
        user_id = uuid.UUID(payload["sub"])
    except (ValueError, KeyError):
        raise credentials_exception
    user = await user_repo.get_active_by_id(user_id)

    if not user:
        raise credentials_exception

    return user


async def get_auth_service(
    db: AsyncSession = Depends(get_db_session),
) -> AuthService:
    user_repo = UserRepository(db)
    token_repo = AuthTokenRepository(db)
    return AuthService(
        session=db,
        user_repo=user_repo,
        token_repo=token_repo,
    )


async def get_asset_service(
    db: AsyncSession = Depends(get_db_session),
) -> AssetService:
    asset_repo = AssetRepository(db)
    return AssetService(session=db, asset_repo=asset_repo)
```

### api/router.py — Complete Implementation

```python
# backend/app/api/router.py
from fastapi import APIRouter

from backend.app.api.v1 import (
    health,
    auth,
    scans,
    findings,
    signals,
    scores,
    account,
    billing,
    legal,
)
from backend.app.billing.webhooks import router as webhooks_router

api_router = APIRouter()

# Health — no prefix, no auth
api_router.include_router(health.router)

# Webhooks — no auth (Stripe signs requests)
api_router.include_router(webhooks_router, prefix="/api/v1")

# Authenticated API endpoints
api_router.include_router(auth.router, prefix="/api/v1")
api_router.include_router(scans.router, prefix="/api/v1")
api_router.include_router(findings.router, prefix="/api/v1")
api_router.include_router(signals.router, prefix="/api/v1")
api_router.include_router(scores.router, prefix="/api/v1")
api_router.include_router(account.router, prefix="/api/v1")
api_router.include_router(billing.router, prefix="/api/v1")
api_router.include_router(legal.router, prefix="/api/v1")
```

### core/schemas.py — Shared Pagination

```python
# backend/app/core/schemas.py
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
```

### db/models/audit.py — Correct Module Location

**The AuditEvent model lives at `backend/app/db/models/audit.py`, NOT at `backend/app/auth/models.py`.**
Create `backend/app/db/models/` as a package with `__init__.py`.

### Scan Model — Correct Location

**The Scan model lives at `backend/app/jobs/models.py`, NOT at `backend/app/auth/models.py`.**
The import is `from backend.app.jobs.models import Scan`.

```python
# backend/app/jobs/models.py
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

### assets/service.py — Complete Implementation

```python
# backend/app/assets/service.py
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.assets.models import Asset
from backend.app.db.repositories.assets import AssetRepository
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class AssetService:
    def __init__(self, session: AsyncSession, asset_repo: AssetRepository) -> None:
        self.session = session
        self.asset_repo = asset_repo

    async def register_verified_email(
        self, user_id: uuid.UUID, email: str
    ) -> Asset:
        """
        Idempotent. Calling this multiple times for the same email
        simply returns the existing asset (updating is_verified if needed).
        Called exclusively by the auth flow after successful OTP verification.
        Do NOT call this from any other location.
        """
        existing = await self.asset_repo.get_by_value(
            user_id=user_id,
            entity_type="email",
            value=email,
        )

        if existing:
            if not existing.is_verified:
                existing.is_verified = True
                existing.verified_at = datetime.now(timezone.utc)
                await self.session.commit()
                logger.info("asset.email_reverified", user_id=str(user_id))
            return existing

        # Check if user already has a primary email
        primary_exists = await self.asset_repo.get_primary_email(user_id)

        asset = Asset(
            user_id=user_id,
            entity_type="email",
            value=email,
            is_primary=(primary_exists is None),  # First email is primary
            is_verified=True,
            verified_at=datetime.now(timezone.utc),
        )
        self.session.add(asset)
        await self.session.commit()
        logger.info("asset.email_registered", user_id=str(user_id))
        return asset
```

### automation/engine.py — Stub

```python
# backend/app/automation/engine.py
"""
Automation engine stub. Not implemented in MVP.
Automation workflows will be added post-MVP.
Do not implement any workflow logic here during the MVP build.
"""
```

---

## ALEMBIC SETUP — EXACT COMMANDS

Run these commands in order after Stage 1 scaffold is complete:

```bash
# 1. Initialise Alembic (run once, from repo root)
uv run alembic init backend/app/db/migrations

# 2. Edit alembic.ini — set sqlalchemy.url
# Change the line: sqlalchemy.url = driver://user:pass@localhost/dbname
# To: sqlalchemy.url = postgresql+psycopg2://zima:zima_dev_password@localhost:5432/zima_dev

# 3. Edit backend/app/db/migrations/env.py
# Replace the target_metadata = None line with:
# from backend.app.db.base import Base
# target_metadata = Base.metadata

# 4. Create the initial migration (after all models are defined in Stage 1-3)
uv run alembic revision --autogenerate -m "initial_schema"

# 5. Apply migrations to dev database
uv run alembic upgrade head

# 6. Verify — this should show "head" with no pending migrations
uv run alembic current
```

Run `alembic revision --autogenerate` and `alembic upgrade head` after EVERY model change. Do not accumulate model changes across stages without migrating.

---

## ABSTRACT BASE CLASS PATTERN — DO NOT CHANGE

The following classes use `...` as the abstract method body. This is **valid Python syntax** for abstract methods — do not replace `...` with `pass` or with an implementation. The concrete subclasses provide the implementations.

```python
# CORRECT — do not change
class BaseModuleService(ABC):
    @abstractmethod
    async def run(self, ...) -> list[SignalCreate]:
        ...

class BaseCorrelationRule(ABC):
    @abstractmethod
    def evaluate(self, ...) -> Finding | None:
        ...
```

---

## DEPENDENCY INJECTION — EXACT PATTERN

Every service that requires database access must be constructed via a FastAPI dependency function defined in `api/dependencies.py`. The pattern is always:

```python
# In api/dependencies.py
async def get_some_service(
    db: AsyncSession = Depends(get_db_session),
) -> SomeService:
    repo = SomeRepository(db)
    return SomeService(session=db, repo=repo)

# In api/v1/endpoint.py
@router.post("/")
async def my_endpoint(
    service: SomeService = Depends(get_some_service),
):
    ...
```

Never construct a service or repository directly inside an endpoint function body. Always use `Depends()`.

---

## BACKGROUND TASK PATTERN — MANDATORY

Every background task function MUST follow this exact pattern. No exceptions.

```python
# CORRECT
async def my_background_task(user_id: uuid.UUID, other_param: str) -> None:
    from backend.app.db.session import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        repo = MyRepository(session)
        await repo.do_work()
        await session.commit()

# WRONG — never do this
async def my_background_task(
    session: AsyncSession,  # ← NEVER pass a session as a parameter
    user_id: uuid.UUID,
) -> None:
    ...
```

Background tasks receive only serialisable parameters (UUIDs, strings, enums). They create their own sessions internally.

---

## IMPORT RULES — ENFORCED BY CI

Violations will fail CI and the pre-commit hook. Do not write these imports regardless of whether they seem necessary:

| Layer | Must NEVER import from |
|---|---|
| `providers/` | `modules`, `correlation`, `scoring`, `remediation`, `automation`, `api` |
| `modules/` | `correlation`, `scoring`, `remediation`, `automation`, `api` |
| `correlation/` | `scoring`, `remediation`, `automation`, `api` |
| `scoring/` | `remediation`, `automation`, `api` |
| `remediation/` | `automation`, `api` |
| `automation/` | `api` |

---

## WHAT TO DO WHEN YOU ARE UNSURE

1. Stop. Do not generate code.
2. Re-read this document.
3. Re-read the relevant section of the stage file.
4. If still unclear, output: `CLARIFICATION NEEDED: [specific question]` and wait.

Do not guess. Do not infer. Do not add "improvements" beyond what is specified.

---

## VERIFICATION COMMANDS BY STAGE

Run the appropriate verification command at the end of each stage. Do not proceed until it passes.

```bash
# After Stage 0
uv run python scripts/check_imports.py
uv run ruff check .
uv run mypy backend/

# After Stage 1
uv run alembic upgrade head
uv run python -c "from backend.app.main import app; print('App imports OK')"
curl http://localhost:8000/health  # With uvicorn running

# After Stage 2
uv run pytest tests/unit/auth/ -v
uv run pytest tests/api/test_auth_endpoints.py -v

# After Stage 3
uv run alembic revision --autogenerate -m "signal_pipeline" --check
uv run pytest tests/unit/signals/ -v

# After Stage 4
uv run pytest tests/unit/modules/ -v

# After Stage 5
uv run pytest tests/unit/correlation/ tests/unit/scoring/ -v

# After Stage 6
uv run pytest tests/integration/ -v
uv run pytest tests/api/test_scan_endpoints.py tests/api/test_findings_endpoints.py -v

# After Stage 7
uv run pytest tests/api/test_account_endpoints.py -v

# Final — all tests
uv run pytest --cov=backend --cov-fail-under=70 -v
uv run python scripts/check_imports.py
uv run pip-audit
```
