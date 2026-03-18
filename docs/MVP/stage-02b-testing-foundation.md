# Stage 2b — Testing Foundation

Complete this before writing any tests. The conftest and factory patterns defined here are used by every subsequent test file. Writing test infrastructure first prevents duplication and inconsistency across 100+ tests.

---

## conftest.py

This is the single most important test file in the project. It defines the fixtures that every test depends on. Define it fully before Stage 2 tests.

```python
# tests/conftest.py
import asyncio
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine,
)
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.db.base import Base
from backend.app.db.session import get_db_session
from backend.app.core.config import settings

# ─── Engine ───────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session")
async def test_engine() -> AsyncGenerator[AsyncEngine, None]:
    """
    One engine for the entire test session.
    Creates all tables at start, drops all at end.
    Uses a dedicated test database — never the dev database.
    """
    assert settings.is_testing, (
        "Tests must run with APP_ENV=testing. "
        "Set this in the CI environment or your local .env.test file."
    )
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ─── Session ─────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """
    One session per test, rolled back after.
    Each test starts with a clean, consistent state.
    """
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    async with session_factory() as session:
        yield session
        await session.rollback()


# ─── HTTP Client ──────────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Unauthenticated HTTP client. Use for testing public endpoints
    and authentication failures.
    """
    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def auth_client(
    client: AsyncClient,
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """
    Authenticated HTTP client. Creates a test user, issues a JWT,
    and adds the Authorization header.
    Use for testing endpoints that require authentication.
    """
    from tests.factories import UserFactory
    from backend.app.auth.utils import create_access_token

    user = UserFactory.build()
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()  # Must commit so get_active_by_id can find the user across sessions

    token = create_access_token(subject=str(user.id), tier=user.tier)
    client.headers["Authorization"] = f"Bearer {token}"

    # Store user on the client for access in tests
    client.test_user = user  # type: ignore[attr-defined]

    yield client


@pytest_asyncio.fixture
async def paid_auth_client(
    client: AsyncClient,
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """
    Authenticated client with a paid tier (shield).
    Use for testing tier-gated functionality.
    """
    from tests.factories import UserFactory
    from backend.app.auth.utils import create_access_token

    user = UserFactory.build(tier="shield")
    db_session.add(user)
    await db_session.flush()
    await db_session.commit()  # Must commit so get_active_by_id can find the user across sessions

    token = create_access_token(subject=str(user.id), tier=user.tier)
    client.headers["Authorization"] = f"Bearer {token}"
    client.test_user = user  # type: ignore[attr-defined]

    yield client


# ─── Utility Fixtures ─────────────────────────────────────────────────────────

@pytest_asyncio.fixture
async def verified_email_asset(db_session: AsyncSession, auth_client: AsyncClient):
    """
    Creates a verified email asset attached to the authenticated test user.
    Use as a prerequisite for scan and signal tests.
    """
    from tests.factories import AssetFactory
    user = auth_client.test_user  # type: ignore[attr-defined]

    asset = AssetFactory.build(
        user_id=user.id,
        entity_type="email",
        value="test@example.com",
        is_verified=True,
    )
    db_session.add(asset)
    await db_session.flush()
    return asset


@pytest.fixture
def mock_hibp_no_breaches(respx_mock):
    """Mocks HIBP to return no breaches for any email."""
    import respx
    import httpx
    respx_mock.get(
        url__regex=r"https://haveibeenpwned\.com/api/v3/breachedaccount/.*"
    ).mock(return_value=httpx.Response(404))
    return respx_mock


@pytest.fixture
def mock_hibp_with_breaches(respx_mock):
    """Mocks HIBP to return two breaches — one with passwords, one without."""
    import respx
    import httpx
    import json
    respx_mock.get(
        url__regex=r"https://haveibeenpwned\.com/api/v3/breachedaccount/.*"
    ).mock(
        return_value=httpx.Response(
            200,
            content=json.dumps([
                {
                    "Name": "Adobe",
                    "Title": "Adobe",
                    "Domain": "adobe.com",
                    "BreachDate": "2013-10-04",
                    "AddedDate": "2013-12-04T00:00:00Z",
                    "DataClasses": ["Email addresses", "Password hints", "Passwords"],
                    "IsVerified": True,
                    "IsSensitive": False,
                    "IsRetired": False,
                    "IsFabricated": False,
                    "PwnCount": 152445165,
                    "Description": "Test breach",
                },
                {
                    "Name": "LinkedIn",
                    "Title": "LinkedIn",
                    "Domain": "linkedin.com",
                    "BreachDate": "2012-05-05",
                    "AddedDate": "2016-05-21T21:35:40Z",
                    "DataClasses": ["Email addresses", "Passwords"],
                    "IsVerified": True,
                    "IsSensitive": False,
                    "IsRetired": False,
                    "IsFabricated": False,
                    "PwnCount": 164611595,
                    "Description": "Test breach",
                },
            ]).encode(),
        )
    )
    return respx_mock


@pytest.fixture
def mock_hibp_rate_limit(respx_mock):
    """Mocks HIBP returning 429 — tests retry and rate limit handling."""
    import respx
    import httpx
    respx_mock.get(
        url__regex=r"https://haveibeenpwned\.com/api/v3/breachedaccount/.*"
    ).mock(return_value=httpx.Response(429))
    return respx_mock
```

---

## Test Factories

```python
# tests/factories.py
import uuid
import factory
from factory import Factory, LazyAttribute, Sequence, SubFactory
from datetime import datetime, timezone
from backend.app.auth.models import User, AuthToken
from backend.app.assets.models import Asset
from backend.app.signals.models import Signal
from backend.app.correlation.models import Finding
from backend.app.scoring.models import Score
from backend.app.db.models.audit import AuditEvent


class UserFactory(Factory):
    class Meta:
        model = User

    id = LazyAttribute(lambda _: uuid.uuid4())
    tier = "core"
    is_active = True
    deleted_at = None
    last_sign_in_at = None


class AuthTokenFactory(Factory):
    class Meta:
        model = AuthToken

    id = LazyAttribute(lambda _: uuid.uuid4())
    email = Sequence(lambda n: f"user{n}@example.com")
    code_hash = LazyAttribute(
        lambda _: __import__("hashlib").sha256(b"123456").hexdigest()
    )
    expires_at = LazyAttribute(
        lambda _: datetime.now(timezone.utc).replace(
            year=datetime.now(timezone.utc).year + 1
        )
    )
    used_at = None
    requested_from_ip = "127.0.0.1"


class AssetFactory(Factory):
    class Meta:
        model = Asset

    id = LazyAttribute(lambda _: uuid.uuid4())
    user_id = LazyAttribute(lambda _: uuid.uuid4())
    entity_type = "email"
    value = Sequence(lambda n: f"asset{n}@example.com")
    is_primary = False
    is_verified = True
    verified_at = LazyAttribute(lambda _: datetime.now(timezone.utc))


class SignalFactory(Factory):
    class Meta:
        model = Signal

    id = LazyAttribute(lambda _: uuid.uuid4())
    signal_id = Sequence(lambda n: f"sig_{n:024x}")
    signal_type = "email_breached"
    category = "identity_security"
    entity_type = "email"
    entity_id = LazyAttribute(lambda _: uuid.uuid4())
    entity_value = Sequence(lambda n: f"user{n}@example.com")
    user_id = LazyAttribute(lambda _: uuid.uuid4())
    severity = "high"
    confidence = "high"
    source = "breach_monitor"
    provider = "hibp"
    summary = "Email found in test breach"
    details = None
    evidence = {}
    tags = ["identity", "breach"]
    recommended_action = "Rotate credentials"
    status = "open"


class FindingFactory(Factory):
    class Meta:
        model = Finding

    id = LazyAttribute(lambda _: uuid.uuid4())
    finding_id = Sequence(lambda n: f"fnd_{n:024x}")
    finding_type = "high_identity_compromise_risk"
    user_id = LazyAttribute(lambda _: uuid.uuid4())
    severity = "high"
    confidence = "high"
    title = "Test finding"
    explanation = "Test explanation"
    contributing_signal_ids = []
    affected_entity_ids = []
    rule_name = "high_identity_compromise_risk"
    status = "open"


class ScoreFactory(Factory):
    class Meta:
        model = Score

    id = LazyAttribute(lambda _: uuid.uuid4())
    user_id = LazyAttribute(lambda _: uuid.uuid4())
    domain = "identity"
    score = 100
    scorer_version = "1.0"
    signal_count = 0
    scan_id = None
```

---

## Test File Structure Convention

Every test file follows this naming and structure convention:

```
tests/
├── conftest.py                          ← shared fixtures (this file)
├── factories.py                         ← model factories (this file)
├── unit/
│   ├── auth/
│   │   ├── test_service.py
│   │   └── test_utils.py
│   ├── signals/
│   │   ├── test_dedup.py
│   │   └── test_schemas.py
│   ├── modules/
│   │   └── identity/
│   │       └── test_breach_monitor.py
│   ├── correlation/
│   │   └── test_rules.py
│   └── scoring/
│       └── test_calculators.py
├── integration/
│   ├── test_scan_pipeline.py            ← end-to-end pipeline test
│   └── test_auth_flow.py               ← full OTP sign-in flow
└── api/
    ├── test_auth_endpoints.py
    ├── test_scan_endpoints.py
    ├── test_findings_endpoints.py
    └── test_account_endpoints.py
```

**Unit tests** mock external dependencies. They are fast and test one thing.

**Integration tests** use the real test database and test multiple layers together. They are slower but catch interface mismatches.

**API tests** use the `client` or `auth_client` fixtures and test through the HTTP interface. They catch routing, middleware, and serialisation issues.

---

## pytest.ini_options (addition to pyproject.toml)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "session"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
filterwarnings = [
    "error",                                    # Treat all warnings as errors
    "ignore::DeprecationWarning:httpx",
    "ignore::DeprecationWarning:sqlalchemy",
]
```

`asyncio_mode = "auto"` means every `async def test_*` is automatically treated as an async test — no need to decorate with `@pytest.mark.asyncio`.

`asyncio_default_fixture_loop_scope = "session"` and `asyncio_default_test_loop_scope = "session"` ensure the session-scoped `test_engine` fixture shares the same event loop as tests. Without this, asyncpg raises `RuntimeError: Task got Future attached to a different loop` when API tests hit the database.

`filterwarnings = ["error"]` catches deprecation warnings before they become breaking changes.
