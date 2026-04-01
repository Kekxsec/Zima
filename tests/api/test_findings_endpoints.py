# tests/api/test_findings_endpoints.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_findings_requires_authentication(client: AsyncClient) -> None:
    response = await client.get("/api/v1/findings/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_findings_returns_empty_for_new_user(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get("/api/v1/findings/")
    assert response.status_code == 200
    data = response.json()
    assert data["findings"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_get_findings_defaults_to_open_status(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get("/api/v1/findings/")
    assert response.status_code == 200
    assert response.json()["filter_status"] == "open"


@pytest.mark.asyncio
async def test_get_findings_rejects_invalid_status_filter(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get("/api/v1/findings/?filter_status=invalid")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_suppress_finding_returns_404_for_nonexistent(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.patch(
        "/api/v1/findings/sig_nonexistent/suppress",
        json={"reason": "test"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_scores_returns_empty_for_new_user(
    auth_client: AsyncClient,
) -> None:
    response = await auth_client.get("/api/v1/scores/")
    assert response.status_code == 200
    assert response.json()["scores"] == []
