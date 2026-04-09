# tests/api/test_assets_endpoints.py
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.app.assets.models import Asset


@pytest.mark.asyncio
async def test_declare_username_creates_unverified_asset(
    auth_client: AsyncClient,
    db_session,
) -> None:
    response = await auth_client.post(
        "/api/v1/assets",
        json={"entity_type": "username", "value": "Alice"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["entity_type"] == "username"
    assert body["value"] == "alice"
    assert body["is_verified"] is False

    result = await db_session.execute(
        select(Asset).where(
            Asset.user_id == auth_client.test_user.id,  # type: ignore[attr-defined]
            Asset.entity_type == "username",
            Asset.value == "alice",
        )
    )
    asset = result.scalar_one()
    assert asset.is_verified is False


@pytest.mark.asyncio
async def test_declare_phone_number_is_rejected(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.post(
        "/api/v1/assets",
        json={"entity_type": "phone_number", "value": "+441234567890"},
    )

    assert response.status_code == 422
    assert "cannot be declared via this endpoint" in response.json()["detail"]


@pytest.mark.asyncio
async def test_declare_device_creates_verified_asset(
    auth_client: AsyncClient,
    db_session,
) -> None:
    response = await auth_client.post(
        "/api/v1/assets",
        json={"entity_type": "device", "value": "Max's MacBook Pro"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["entity_type"] == "device"
    assert body["value"] == "Max's MacBook Pro"
    assert body["is_verified"] is True

    result = await db_session.execute(
        select(Asset).where(
            Asset.user_id == auth_client.test_user.id,  # type: ignore[attr-defined]
            Asset.entity_type == "device",
            Asset.value == "Max's MacBook Pro",
        )
    )
    asset = result.scalar_one()
    assert asset.is_verified is True


@pytest.mark.asyncio
async def test_declare_browser_extension_url_normalises_to_scanable_asset(
    auth_client: AsyncClient,
    db_session,
) -> None:
    response = await auth_client.post(
        "/api/v1/assets",
        json={
            "entity_type": "url",
            "value": "https://chromewebstore.google.com/detail/ublock-origin/cjpalhdlnbpafiamejdnhcphjbkeiagm",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["entity_type"] == "url"
    assert body["value"] == "cjpalhdlnbpafiamejdnhcphjbkeiagm:latest:chrome"
    assert body["is_verified"] is True

    result = await db_session.execute(
        select(Asset).where(
            Asset.user_id == auth_client.test_user.id,  # type: ignore[attr-defined]
            Asset.entity_type == "url",
            Asset.value == "cjpalhdlnbpafiamejdnhcphjbkeiagm:latest:chrome",
        )
    )
    asset = result.scalar_one()
    assert asset.is_verified is True


@pytest.mark.asyncio
async def test_declare_invalid_browser_extension_url_is_rejected(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.post(
        "/api/v1/assets",
        json={"entity_type": "url", "value": "https://example.com/not-an-extension"},
    )

    assert response.status_code == 422
    assert "Browser extension input" in response.json()["detail"]


@pytest.mark.asyncio
async def test_verify_phone_asset_rejects_non_numeric_code(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.post(
        "/api/v1/assets/phone/otp/verify",
        json={"phone": "+441234567890", "code": "abcdef"},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_verify_email_asset_rejects_non_numeric_code(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.post(
        "/api/v1/assets/email/otp/verify",
        json={"email": "test@example.com", "code": "abcdef"},
    )

    assert response.status_code == 422
