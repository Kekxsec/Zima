# tests/api/test_auth_endpoints.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_request_otp_always_returns_202(client: AsyncClient) -> None:
    """Returns 202 regardless of whether email exists or rate limit applies."""
    response = await client.post(
        "/api/v1/auth/otp/request",
        json={"email": "any@example.com", "privacy_policy_accepted": True},
    )
    assert response.status_code == 202
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_request_otp_rejects_invalid_email(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/otp/request",
        json={"email": "not-an-email"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_verify_otp_rejects_non_numeric_code(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/otp/verify",
        json={"email": "test@example.com", "code": "abcdef"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_verify_otp_rejects_wrong_length_code(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/otp/verify",
        json={"email": "test@example.com", "code": "12345"},  # 5 digits, not 6
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_verify_otp_returns_401_for_wrong_code(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/otp/verify",
        json={"email": "test@example.com", "code": "000000"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired code."


@pytest.mark.asyncio
async def test_authenticated_endpoint_rejects_missing_token(
    client: AsyncClient,
) -> None:
    """Verifies the auth dependency works on a protected endpoint."""
    response = await client.get("/api/v1/account/audit-log")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_endpoint_rejects_invalid_token(
    client: AsyncClient,
) -> None:
    response = await client.get(
        "/api/v1/account/audit-log",
        headers={"Authorization": "Bearer invalidtoken"},
    )
    assert response.status_code == 401
