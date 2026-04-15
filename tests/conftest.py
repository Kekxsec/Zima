# tests/conftest.py
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
import redis as redis_sync
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.core.config import settings
from backend.app.db.base import Base
from backend.app.db.session import get_db_session
from backend.app.jobs.models import (
    Scan,  # noqa: F401 — registers Scan table in Base.metadata
)
from backend.app.main import app

# ─── Rate Limit Reset ─────────────────────────────────────────────────────────


@pytest.fixture(scope="session", autouse=True)
def flush_rate_limit_keys() -> None:
    """
    Delete all slowapi rate-limit keys for the test client IP (127.0.0.1)
    before the test session begins. Prevents counter bleed between runs.
    Local integration and API tests expect Redis from docker-compose.yml and
    APP_ENV=testing from .env.test.
    """
    try:
        r = redis_sync.from_url(settings.redis_url)
        for key in r.scan_iter("*127.0.0.1*"):
            r.delete(key)
        r.close()
    except redis_sync.RedisError as exc:
        raise RuntimeError(
            "Redis is required for the default pytest fixtures. "
            "Start services with `docker compose up -d --force-recreate postgres redis`, "
            "then load `.env.test` so APP_ENV=testing and REDIS_URL point at the local test stack."
        ) from exc


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
        "Set this in the CI environment or load your local .env.test file before running pytest."
    )
    engine = create_async_engine(settings.database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ─── Session ──────────────────────────────────────────────────────────────────


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
    from backend.app.auth.utils import create_access_token
    from tests.factories import UserFactory

    user = UserFactory.build()
    db_session.add(user)
    await db_session.flush()
    await (
        db_session.commit()
    )  # Must commit so get_active_by_id can find the user across sessions

    token = create_access_token(subject=str(user.id), tier=user.tier)
    client.headers["Authorization"] = f"Bearer {token}"

    # Store user on the client for access in tests
    client.test_user = user  # type: ignore[attr-defined]

    yield client


@pytest_asyncio.fixture
async def paid_auth_client(
    test_engine: AsyncEngine,
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient, None]:
    """
    Authenticated client with a paid tier (pro).
    Independent AsyncClient so it does not share auth headers with auth_client.
    Use for testing tier-gated functionality and cross-user isolation.
    """
    from backend.app.auth.utils import create_access_token
    from tests.factories import UserFactory

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db

    user = UserFactory.build(tier="pro")
    db_session.add(user)
    await db_session.flush()
    await (
        db_session.commit()
    )  # Must commit so get_active_by_id can find the user across sessions

    token = create_access_token(subject=str(user.id), tier=user.tier)
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        c.test_user = user  # type: ignore[attr-defined]
        yield c
    app.dependency_overrides.clear()


# ─── Utility Fixtures ─────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def verified_email_asset(db_session: AsyncSession, auth_client: AsyncClient):  # type: ignore[type-arg]
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
def mock_hibp_no_breaches(respx_mock):  # type: ignore[no-untyped-def]
    """Mocks HIBP to return no breaches for any email."""
    from unittest.mock import patch

    import httpx
    from pydantic import SecretStr

    respx_mock.get(
        url__regex=r"https://haveibeenpwned\.com/api/v3/breachedaccount/.*"
    ).mock(return_value=httpx.Response(404))
    respx_mock.get(url__regex=r"https://leakcheck\.io/api/public\?check=.*").mock(
        return_value=httpx.Response(
            200, json={"success": True, "found": 0, "sources": []}
        )
    )
    with patch(
        "backend.app.modules.identity.breach_monitor.service.settings"
    ) as mock_settings:
        mock_settings.hibp_api_key = SecretStr("test-key")
        mock_settings.dehashed_email = None
        mock_settings.dehashed_api_key = None
        mock_settings.breachdirectory_rapidapi_key = None
        mock_settings.leakcheck_api_key = None
        yield respx_mock
    return


@pytest.fixture
def mock_hibp_with_breaches(respx_mock):  # type: ignore[no-untyped-def]
    """Mocks HIBP to return two breaches — one with passwords, one without."""
    import json
    from unittest.mock import patch

    import httpx
    from pydantic import SecretStr

    respx_mock.get(
        url__regex=r"https://haveibeenpwned\.com/api/v3/breachedaccount/.*"
    ).mock(
        return_value=httpx.Response(
            200,
            content=json.dumps(
                [
                    {
                        "Name": "Adobe",
                        "Title": "Adobe",
                        "Domain": "adobe.com",
                        "BreachDate": "2013-10-04",
                        "AddedDate": "2013-12-04T00:00:00Z",
                        "DataClasses": [
                            "Email addresses",
                            "Password hints",
                            "Passwords",
                        ],
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
                ]
            ).encode(),
        )
    )
    respx_mock.get(url__regex=r"https://leakcheck\.io/api/public\?check=.*").mock(
        return_value=httpx.Response(
            200, json={"success": True, "found": 0, "sources": []}
        )
    )
    with patch(
        "backend.app.modules.identity.breach_monitor.service.settings"
    ) as mock_settings:
        mock_settings.hibp_api_key = SecretStr("test-key")
        mock_settings.dehashed_email = None
        mock_settings.dehashed_api_key = None
        mock_settings.breachdirectory_rapidapi_key = None
        mock_settings.leakcheck_api_key = None
        yield respx_mock
    return


@pytest.fixture
def mock_hibp_rate_limit(respx_mock):  # type: ignore[no-untyped-def]
    """Mocks HIBP returning 429 — tests retry and rate limit handling."""
    import httpx

    respx_mock.get(
        url__regex=r"https://haveibeenpwned\.com/api/v3/breachedaccount/.*"
    ).mock(return_value=httpx.Response(429))
    return respx_mock
