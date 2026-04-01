# tests/api/test_scan_endpoints.py
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from backend.app.jobs.models import Scan
from tests.factories import AssetFactory


@pytest.mark.asyncio
async def test_trigger_scan_requires_authentication(client: AsyncClient) -> None:
    response = await client.post("/api/v1/scans/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_trigger_scan_returns_202_with_scan_id(
    auth_client: AsyncClient,
    db_session,
) -> None:
    user = auth_client.test_user  # type: ignore[attr-defined]
    db_session.add(
        AssetFactory.build(
            user_id=user.id,
            entity_type="email",
            value="scan-target@example.com",
            is_verified=True,
        )
    )
    await db_session.commit()

    with patch("backend.app.api.v1.scans.run_scan_task"):
        response = await auth_client.post("/api/v1/scans/")
    assert response.status_code == 202
    data = response.json()
    assert "scan_id" in data
    assert data["status"] == "pending"
    assert data["target_emails"] == ["scan-target@example.com"]


@pytest.mark.asyncio
async def test_trigger_scan_enqueues_background_task(
    auth_client: AsyncClient,
    db_session,
) -> None:
    """Background task must be added — session must NOT be passed to it."""
    user = auth_client.test_user  # type: ignore[attr-defined]
    asset = AssetFactory.build(
        user_id=user.id,
        entity_type="email",
        value="queued-target@example.com",
        is_verified=True,
    )
    db_session.add(asset)
    await db_session.commit()

    with patch("backend.app.api.v1.scans.run_scan_task") as mock_task:
        await auth_client.post("/api/v1/scans/")
    mock_task.assert_called_once()
    assert "session" not in mock_task.call_args.kwargs
    assert mock_task.call_args.kwargs["target_email_asset_ids"] == [str(asset.id)]


@pytest.mark.asyncio
async def test_get_scan_history_returns_empty_for_new_user(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get("/api/v1/scans/")
    assert response.status_code == 200
    assert response.json()["scans"] == []


@pytest.mark.asyncio
async def test_get_scan_status_returns_404_for_unknown_id(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get(
        "/api/v1/scans/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_scan_status_returns_404_for_other_users_scan(
    auth_client: AsyncClient,
    paid_auth_client: AsyncClient,
) -> None:
    """User A cannot access User B's scan."""
    with patch("backend.app.api.v1.scans.run_scan_task"):
        create_resp = await auth_client.post("/api/v1/scans/")
    scan_id = create_resp.json()["scan_id"]

    response = await paid_auth_client.get(f"/api/v1/scans/{scan_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_scan_status_returns_422_for_invalid_uuid(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get("/api/v1/scans/not-a-uuid")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_scan_history_includes_target_emails(
    auth_client: AsyncClient,
    db_session,
) -> None:
    user = auth_client.test_user  # type: ignore[attr-defined]
    scan = Scan(
        user_id=user.id,
        tier="core",
        status="completed",
        target_emails=["first@example.com", "second@example.com"],
    )
    db_session.add(scan)
    await db_session.commit()

    response = await auth_client.get("/api/v1/scans/")
    assert response.status_code == 200
    assert response.json()["scans"][0]["target_emails"] == [
        "first@example.com",
        "second@example.com",
    ]
