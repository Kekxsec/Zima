# tests/api/test_email_accounts_endpoints.py
"""API tests for the email account identifier endpoints."""

import csv
import io
import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.email_accounts import DiscoveredAccount, ServiceRegistry
from backend.app.db.session import get_db_session
from backend.app.main import app
from tests.factories import AssetFactory, SignalFactory, UserFactory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mbox(*messages: tuple[str, str, str]) -> bytes:
    """Build minimal mbox bytes from (from_addr, subject, date_str) tuples."""
    lines: list[bytes] = []
    for from_addr, subject, date_str in messages:
        lines.append(f"From {from_addr} {date_str}\n".encode())
        lines.append(f"From: {from_addr}\n".encode())
        lines.append(f"Subject: {subject}\n".encode())
        lines.append(f"Date: {date_str}\n".encode())
        lines.append(b"Message-ID: <test@example.com>\n")
        lines.append(b"\n")
        lines.append(b"Body.\n\n")
    return b"".join(lines)


def _mbox_file(data: bytes, filename: str = "test.mbox") -> dict:
    """Return httpx files= dict for multipart upload."""
    return {"file": (filename, io.BytesIO(data), "application/mbox")}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def plus_client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """
    Authenticated client with a 'plus' tier user + verified primary email asset.
    """
    from httpx import ASGITransport
    from httpx import AsyncClient as HxClient

    from backend.app.auth.utils import create_access_token

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db

    user = UserFactory.build(tier="plus")
    db_session.add(user)
    asset = AssetFactory.build(
        user_id=user.id,
        entity_type="email",
        value="plus@example.com",
        is_verified=True,
        is_primary=True,
    )
    db_session.add(asset)
    await db_session.flush()
    await db_session.commit()

    token = create_access_token(subject=str(user.id), tier=user.tier)
    async with HxClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"},
    ) as c:
        c.test_user = user  # type: ignore[attr-defined]
        c.test_asset = asset  # type: ignore[attr-defined]
        yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Auth / access
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_requires_auth(client: AsyncClient) -> None:
    data = _make_mbox(("a@b.com", "Hi", "Mon, 01 Jan 2024 00:00:00 +0000"))
    response = await client.post(
        "/api/v1/email-accounts/uploads", files=_mbox_file(data)
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_allowed_for_core_tier(
    auth_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = auth_client.test_user  # type: ignore[attr-defined]
    db_session.add(
        AssetFactory.build(
            user_id=user.id,
            entity_type="email",
            value="core@example.com",
            is_verified=True,
            is_primary=True,
        )
    )
    await db_session.commit()

    data = _make_mbox(("a@b.com", "Hi", "Mon, 01 Jan 2024 00:00:00 +0000"))
    with patch("backend.app.api.v1.email_accounts.process_mbox_upload"):
        response = await auth_client.post(
            "/api/v1/email-accounts/uploads", files=_mbox_file(data)
        )
    assert response.status_code == 202


@pytest.mark.asyncio
async def test_list_uploads_allowed_for_core_tier(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get("/api/v1/email-accounts/uploads")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_accounts_allowed_for_core_tier(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/v1/email-accounts/accounts")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_export_allowed_for_core_tier(auth_client: AsyncClient) -> None:
    response = await auth_client.get("/api/v1/email-accounts/export")
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_upload_empty_file_returns_400(plus_client: AsyncClient) -> None:
    with patch("backend.app.api.v1.email_accounts.process_mbox_upload"):
        response = await plus_client.post(
            "/api/v1/email-accounts/uploads",
            files={"file": ("empty.mbox", io.BytesIO(b""), "application/mbox")},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_upload_unsupported_content_type_returns_415(
    plus_client: AsyncClient,
) -> None:
    with patch("backend.app.api.v1.email_accounts.process_mbox_upload"):
        response = await plus_client.post(
            "/api/v1/email-accounts/uploads",
            files={"file": ("data.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        )
    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_valid_mbox_returns_202(plus_client: AsyncClient) -> None:
    data = _make_mbox(
        ("noreply@github.com", "Welcome to GitHub!", "Mon, 01 Jan 2024 00:00:00 +0000")
    )
    with patch("backend.app.api.v1.email_accounts.process_mbox_upload"):
        response = await plus_client.post(
            "/api/v1/email-accounts/uploads", files=_mbox_file(data)
        )
    assert response.status_code == 202
    body = response.json()
    assert "upload_id" in body
    assert body["status"] == "pending"


@pytest.mark.asyncio
async def test_upload_enqueues_background_task(plus_client: AsyncClient) -> None:
    """process_mbox_upload must be called (as a background task) with the right args."""
    data = _make_mbox(
        ("noreply@github.com", "Welcome to GitHub!", "Mon, 01 Jan 2024 00:00:00 +0000")
    )
    with patch("backend.app.api.v1.email_accounts.process_mbox_upload") as mock_task:
        await plus_client.post("/api/v1/email-accounts/uploads", files=_mbox_file(data))
    mock_task.assert_called_once()
    kwargs = mock_task.call_args.kwargs
    # Rule 3: session must NOT be passed to the background task
    assert "session" not in kwargs
    assert "user_id" in kwargs
    assert "upload_id" in kwargs
    assert "mbox_path" in kwargs
    Path(kwargs["mbox_path"]).unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_upload_same_file_twice_is_idempotent(plus_client: AsyncClient) -> None:
    """Uploading the same mbox twice returns the original upload_id."""
    data = _make_mbox(
        (
            "noreply@dropbox.com",
            "Confirm your Dropbox account",
            "Mon, 01 Jan 2024 00:00:00 +0000",
        )
    )
    with patch("backend.app.api.v1.email_accounts.process_mbox_upload"):
        r1 = await plus_client.post(
            "/api/v1/email-accounts/uploads", files=_mbox_file(data)
        )
        r2 = await plus_client.post(
            "/api/v1/email-accounts/uploads", files=_mbox_file(data)
        )

    assert r1.status_code == 202
    assert r2.status_code == 200  # idempotent → 200 with existing record
    assert r1.json()["upload_id"] == r2.json()["upload_id"]


@pytest.mark.asyncio
async def test_upload_rate_limit_is_scoped_per_authenticated_user(
    plus_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    from backend.app.auth.utils import create_access_token

    other_user = UserFactory.build(tier="plus")
    db_session.add(other_user)
    other_asset = AssetFactory.build(
        user_id=other_user.id,
        entity_type="email",
        value="other-plus@example.com",
        is_verified=True,
        is_primary=True,
    )
    db_session.add(other_asset)
    await db_session.commit()

    token = create_access_token(subject=str(other_user.id), tier=other_user.tier)
    data1 = _make_mbox(("first@service.com", "Hi", "Mon, 01 Jan 2024 00:00:00 +0000"))
    data2 = _make_mbox(("second@service.com", "Hi", "Tue, 02 Jan 2024 00:00:00 +0000"))
    data3 = _make_mbox(("third@service.com", "Hi", "Wed, 03 Jan 2024 00:00:00 +0000"))

    with patch("backend.app.api.v1.email_accounts.process_mbox_upload"):
        r1 = await plus_client.post(
            "/api/v1/email-accounts/uploads", files=_mbox_file(data1)
        )
        r2 = await plus_client.post(
            "/api/v1/email-accounts/uploads", files=_mbox_file(data2)
        )
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {token}"},
        ) as other_client:
            r3 = await other_client.post(
                "/api/v1/email-accounts/uploads",
                files=_mbox_file(data3),
            )

    assert r1.status_code == 202
    assert r2.status_code == 202
    assert r3.status_code == 202


# ---------------------------------------------------------------------------
# List uploads
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_uploads_returns_empty_for_new_user(
    plus_client: AsyncClient,
) -> None:
    response = await plus_client.get("/api/v1/email-accounts/uploads")
    assert response.status_code == 200
    body = response.json()
    assert "uploads" in body
    assert isinstance(body["uploads"], list)


@pytest.mark.asyncio
async def test_list_uploads_shows_created_upload(plus_client: AsyncClient) -> None:
    data = _make_mbox(
        ("noreply@spotify.com", "Welcome to Spotify", "Mon, 01 Jan 2024 00:00:00 +0000")
    )
    with patch("backend.app.api.v1.email_accounts.process_mbox_upload"):
        await plus_client.post("/api/v1/email-accounts/uploads", files=_mbox_file(data))

    response = await plus_client.get("/api/v1/email-accounts/uploads")
    assert response.status_code == 200
    body = response.json()
    assert len(body["uploads"]) >= 1
    upload = body["uploads"][0]
    assert "id" in upload
    assert "status" in upload
    assert "filename" in upload


# ---------------------------------------------------------------------------
# Get upload status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_upload_status_returns_404_for_unknown(
    plus_client: AsyncClient,
) -> None:
    response = await plus_client.get(
        "/api/v1/email-accounts/uploads/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_upload_status_returns_422_for_invalid_id(
    plus_client: AsyncClient,
) -> None:
    response = await plus_client.get("/api/v1/email-accounts/uploads/not-a-uuid")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_upload_status_returns_upload(plus_client: AsyncClient) -> None:
    data = _make_mbox(
        ("noreply@netflix.com", "Welcome to Netflix", "Mon, 01 Jan 2024 00:00:00 +0000")
    )
    with patch("backend.app.api.v1.email_accounts.process_mbox_upload"):
        post_resp = await plus_client.post(
            "/api/v1/email-accounts/uploads", files=_mbox_file(data)
        )
    upload_id = post_resp.json()["upload_id"]

    response = await plus_client.get(f"/api/v1/email-accounts/uploads/{upload_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == upload_id


# ---------------------------------------------------------------------------
# List accounts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_accounts_returns_200_with_structure(
    plus_client: AsyncClient,
) -> None:
    response = await plus_client.get("/api/v1/email-accounts/accounts")
    assert response.status_code == 200
    body = response.json()
    assert "accounts" in body
    assert "total" in body
    assert "limit" in body
    assert "offset" in body


@pytest.mark.asyncio
async def test_list_accounts_pagination_params(plus_client: AsyncClient) -> None:
    response = await plus_client.get("/api/v1/email-accounts/accounts?limit=5&offset=0")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_list_accounts_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/email-accounts/accounts")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Mark account reviewed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mark_reviewed_returns_404_for_unknown(plus_client: AsyncClient) -> None:
    response = await plus_client.patch(
        "/api/v1/email-accounts/accounts/00000000-0000-0000-0000-000000000000/reviewed"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_mark_reviewed_returns_422_for_invalid_id(
    plus_client: AsyncClient,
) -> None:
    response = await plus_client.patch(
        "/api/v1/email-accounts/accounts/not-a-uuid/reviewed"
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_export_returns_csv(plus_client: AsyncClient) -> None:
    response = await plus_client.get("/api/v1/email-accounts/export")
    assert response.status_code == 200
    assert "text/csv" in response.headers.get("content-type", "")
    assert "Content-Disposition" in response.headers
    assert response.headers["Content-Disposition"].endswith('.csv"')


@pytest.mark.asyncio
async def test_export_1password_format(plus_client: AsyncClient) -> None:
    response = await plus_client.get("/api/v1/email-accounts/export?format=1password")
    assert response.status_code == 200
    body = response.text.lstrip("\ufeff")  # strip BOM
    # 1Password format has these headers
    assert "Title" in body
    assert "Website" in body
    assert "Tags" in body


@pytest.mark.asyncio
async def test_export_bitwarden_format(plus_client: AsyncClient) -> None:
    response = await plus_client.get("/api/v1/email-accounts/export?format=bitwarden")
    assert response.status_code == 200
    body = response.text.lstrip("\ufeff")
    assert "login_uri" in body
    assert "folder" in body


@pytest.mark.asyncio
async def test_export_invalid_format_returns_422(plus_client: AsyncClient) -> None:
    response = await plus_client.get("/api/v1/email-accounts/export?format=invalid")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_export_includes_priority_tags_and_verification_guidance(
    plus_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    user = plus_client.test_user  # type: ignore[attr-defined]
    primary_email = plus_client.test_asset.value  # type: ignore[attr-defined]
    now = datetime.now(UTC)

    db_session.add(
        ServiceRegistry(
            service_name="github",
            display_name="GitHub",
            category="developer",
            common_domains=["github.com"],
            login_url="https://github.com/login",
            password_reset_url="https://github.com/password_reset",  # noqa: S106
            is_active=True,
        )
    )
    db_session.add(
        DiscoveredAccount(
            id=uuid.uuid4(),
            user_id=user.id,
            upload_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            service_name="github",
            display_name="GitHub",
            email_used=primary_email,
            source_type="account_confirmation",
            login_url="https://github.com/login",
            password_reset_url="https://github.com/password_reset",  # noqa: S106
            sender_domain="github.com",
            email_count=3,
            first_seen_at=now,
            last_seen_at=now,
            is_reviewed=False,
        )
    )
    db_session.add(
        SignalFactory.build(
            user_id=user.id,
            entity_id=plus_client.test_asset.id,  # type: ignore[attr-defined]
            entity_value=primary_email,
            summary="Email found in GitHub-related breach evidence",
        )
    )
    await db_session.commit()

    response = await plus_client.get("/api/v1/email-accounts/export")
    assert response.status_code == 200

    rows = list(csv.DictReader(io.StringIO(response.text.lstrip("\ufeff"))))
    assert len(rows) == 1
    row = rows[0]

    assert row["priority_label"] == "P2 HIGH"
    assert "zima-review" in row["priority_tags"]
    assert "breached" in row["priority_tags"]
    assert "category:developer" in row["priority_tags"]
    assert "VirusTotal" in row["verification_guidance"]
    assert "rotate the password" in row["recommended_next_step"].lower()


# ---------------------------------------------------------------------------
# Cross-user isolation (IDOR guard)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_alias_for_other_users_account_returns_404(
    auth_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    Attempting to create an alias for an account that belongs to a *different*
    user must return 404, not a provider error or 500.
    """
    from tests.factories import UserFactory

    # Create a second (victim) user and a discovered account owned by them
    victim = UserFactory.build()
    db_session.add(victim)
    await db_session.flush()

    victim_account = DiscoveredAccount(
        user_id=victim.id,
        upload_id=uuid.uuid4(),
        service_name="github.com",
        display_name="GitHub",
        email_used="victim@example.com",
        source_type="mbox",
        sender_domain="github.com",
        email_count=1,
    )
    db_session.add(victim_account)
    await db_session.commit()

    # auth_client is already authenticated as a *different* user
    response = await auth_client.post(
        f"/api/v1/email-accounts/accounts/{victim_account.id}/alias",
        json={"provider": "simplelogin", "mailbox_id": 1},
    )
    assert response.status_code == 404
