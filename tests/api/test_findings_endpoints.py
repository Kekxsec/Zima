# tests/api/test_findings_endpoints.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories import AssetFactory, FindingFactory, SignalFactory, UserFactory


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
async def test_get_findings_returns_supporting_details(
    auth_client: AsyncClient,
    db_session,
) -> None:
    user = auth_client.test_user  # type: ignore[attr-defined]
    asset = AssetFactory.build(
        user_id=user.id,
        entity_type="email",
        value="detail@example.com",
        is_primary=True,
        is_verified=True,
    )
    db_session.add(asset)
    await db_session.flush()

    signal = SignalFactory.build(
        user_id=user.id,
        entity_id=asset.id,
        entity_value=asset.value,
        confidence="high",
        summary="Credential exposure in breach",
        recommended_action="Rotate this password immediately.",
        evidence={
            "breach_name": "Canva",
            "breach_date": "2026-04-07",
            "data_classes": ["Email addresses", "Passwords"],
        },
    )
    db_session.add(signal)

    finding = FindingFactory.build(
        user_id=user.id,
        confidence="high",
        contributing_signal_ids=[signal.signal_id],
        affected_entity_ids=[str(asset.id)],
    )
    db_session.add(finding)
    await db_session.commit()

    response = await auth_client.get("/api/v1/findings/")
    assert response.status_code == 200
    payload = response.json()["findings"][0]
    assert payload["confidence"] == pytest.approx(0.92)
    assert payload["confidence_label"] == "high"
    assert payload["recommended_actions"] == ["Rotate this password immediately."]
    assert payload["supporting_signals"][0]["signal_id"] == signal.signal_id
    assert payload["supporting_signals"][0]["breach_name"] == "Canva"
    assert payload["supporting_signals"][0]["data_classes"] == [
        "Email addresses",
        "Passwords",
    ]
    assert payload["impacted_breaches"][0]["email"] == asset.value
    assert payload["impacted_breaches"][0]["breach_name"] == "Canva"
    assert payload["affected_entities"][0]["value"] == asset.value


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


# ---------------------------------------------------------------------------
# Cross-user isolation (IDOR guard)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_suppress_finding_for_other_users_signal_returns_404(
    auth_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """
    Suppressing a signal that belongs to a different user must return 404.
    The suppress endpoint must not leak signal_ids across tenants.
    """
    victim = UserFactory.build()
    db_session.add(victim)
    victim_asset = AssetFactory.build(
        user_id=victim.id,
        entity_type="email",
        value="victim@example.com",
        is_verified=True,
    )
    db_session.add(victim_asset)
    victim_signal = SignalFactory.build(
        user_id=victim.id,
        entity_id=victim_asset.id,
        entity_value="victim@example.com",
    )
    db_session.add(victim_signal)
    await db_session.commit()

    response = await auth_client.patch(
        f"/api/v1/findings/{victim_signal.signal_id}/suppress",
        json={"reason": "cross-user test"},
    )
    assert response.status_code == 404
