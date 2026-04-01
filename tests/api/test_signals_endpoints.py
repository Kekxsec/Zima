import pytest
from httpx import AsyncClient

from tests.factories import AssetFactory, SignalFactory


@pytest.mark.asyncio
async def test_get_signals_hides_inventory_signal_types(
    auth_client: AsyncClient,
    db_session,
) -> None:
    user = auth_client.test_user  # type: ignore[attr-defined]
    asset = AssetFactory.build(
        user_id=user.id,
        entity_type="email",
        value="signals@example.com",
        is_verified=True,
    )
    db_session.add(asset)
    await db_session.flush()
    db_session.add(
        SignalFactory.build(
            user_id=user.id,
            signal_type="username_exposure",
            category="identity_security",
            entity_id=asset.id,
            entity_value=asset.value,
            summary="Username found on GitHub",
        )
    )
    db_session.add(
        SignalFactory.build(
            user_id=user.id,
            signal_type="email_breached",
            category="identity_security",
            entity_id=asset.id,
            entity_value=asset.value,
            summary="Email found in breach",
        )
    )
    await db_session.commit()

    response = await auth_client.get("/api/v1/signals/")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert len(body["signals"]) == 1
    assert body["signals"][0]["signal_type"] == "email_breached"
