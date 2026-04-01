# tests/api/test_account_endpoints.py
import uuid
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.models import User
from backend.app.tiers.loader import load_tier_config

# ─── Account Deletion ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_account_soft_deletes_user_immediately(
    auth_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """DELETE /account/ returns 202 and immediately marks user as inactive."""
    response = await auth_client.delete("/api/v1/account/")
    assert response.status_code == 202
    assert "deletion initiated" in response.json()["message"]

    user = auth_client.test_user  # type: ignore[attr-defined]
    result = await db_session.execute(select(User).where(User.id == user.id))
    db_user = result.scalar_one()
    assert db_user.is_active is False
    assert db_user.deleted_at is not None


@pytest.mark.asyncio
async def test_delete_account_prevents_subsequent_sign_in(
    auth_client: AsyncClient,
) -> None:
    """After deletion, using the same JWT returns 401."""
    await auth_client.delete("/api/v1/account/")

    # Subsequent authenticated request should fail — user is inactive
    response = await auth_client.get("/api/v1/account/audit-log")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_preserves_user_row_for_audit(
    auth_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """User row is preserved (not hard-deleted) to maintain audit integrity."""
    user = auth_client.test_user  # type: ignore[attr-defined]
    await auth_client.delete("/api/v1/account/")

    # User row should still exist
    result = await db_session.execute(select(User).where(User.id == user.id))
    db_user = result.scalar_one_or_none()
    assert db_user is not None


# ─── Data Export ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_export_returns_all_user_data(
    auth_client: AsyncClient,
) -> None:
    """GET /account/export returns user info with expected keys."""
    response = await auth_client.get("/api/v1/account/export")
    assert response.status_code == 200
    data = response.json()
    assert "user" in data
    assert "assets" in data
    assert "signals" in data
    assert "findings" in data
    assert "scores" in data
    assert str(auth_client.test_user.id) == data["user"]["id"]  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_export_excludes_other_users_data(
    auth_client: AsyncClient,
    paid_auth_client: AsyncClient,
) -> None:
    """Export only returns data for the authenticated user."""
    response_a = await auth_client.get("/api/v1/account/export")
    response_b = await paid_auth_client.get("/api/v1/account/export")

    assert response_a.status_code == 200
    assert response_b.status_code == 200

    user_a_id = response_a.json()["user"]["id"]
    user_b_id = response_b.json()["user"]["id"]
    assert user_a_id != user_b_id


# ─── Stripe Webhook ───────────────────────────────────────────────────────────


def _make_stripe_event(event_type: str, data: dict) -> dict:
    return {
        "id": f"evt_{uuid.uuid4().hex}",
        "type": event_type,
        "data": {"object": data},
    }


@pytest.mark.asyncio
async def test_webhook_rejects_invalid_signature(
    client: AsyncClient,
) -> None:
    """POST /webhooks/stripe with a bad signature returns 400."""
    with patch("backend.app.billing.webhooks.settings") as mock_settings:
        mock_settings.stripe_webhook_secret.get_secret_value.return_value = "whsec_test"
        mock_settings.stripe_webhook_secret = MagicMock()
        mock_settings.stripe_webhook_secret.get_secret_value.return_value = "whsec_test"
        mock_settings.stripe_price_shield_monthly = None
        mock_settings.stripe_price_pro_monthly = None

        response = await client.post(
            "/api/v1/webhooks/stripe",
            content=b'{"type":"test"}',
            headers={"stripe-signature": "bad_sig"},
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_subscription_updated_upgrades_tier(
    auth_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """customer.subscription.updated event updates user tier in database."""
    user = auth_client.test_user  # type: ignore[attr-defined]
    stripe_customer_id = f"cus_{uuid.uuid4().hex}"
    price_id = "price_shield_test"

    # Give the user a stripe_customer_id
    user.stripe_customer_id = stripe_customer_id
    db_session.add(user)
    await db_session.commit()

    event_data = {
        "id": "sub_test",
        "customer": stripe_customer_id,
        "items": {"data": [{"price": {"id": price_id}}]},
    }

    mock_event = _make_stripe_event("customer.subscription.updated", event_data)

    with (
        patch("stripe.Webhook.construct_event", return_value=mock_event),
        patch("backend.app.billing.webhooks.settings") as mock_settings,
    ):
        mock_settings.stripe_webhook_secret = MagicMock()
        mock_settings.stripe_webhook_secret.get_secret_value.return_value = "whsec_test"
        mock_settings.stripe_price_shield_monthly = price_id
        mock_settings.stripe_price_pro_monthly = None

        response = await auth_client.post(
            "/api/v1/webhooks/stripe",
            content=b"{}",
            headers={"stripe-signature": "t=1,v1=sig"},
        )

    assert response.status_code == 200
    assert response.json() == {"received": True}

    # Tier should be updated in db
    await db_session.refresh(user)
    assert user.tier == "shield"


@pytest.mark.asyncio
async def test_subscription_deleted_downgrades_to_core(
    auth_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """customer.subscription.deleted event downgrades user to core."""
    user = auth_client.test_user  # type: ignore[attr-defined]
    stripe_customer_id = f"cus_{uuid.uuid4().hex}"

    user.stripe_customer_id = stripe_customer_id
    user.tier = "shield"
    user.stripe_subscription_id = "sub_old"
    db_session.add(user)
    await db_session.commit()

    event_data = {"id": "sub_old", "customer": stripe_customer_id}
    mock_event = _make_stripe_event("customer.subscription.deleted", event_data)

    with (
        patch("stripe.Webhook.construct_event", return_value=mock_event),
        patch("backend.app.billing.webhooks.settings") as mock_settings,
    ):
        mock_settings.stripe_webhook_secret = MagicMock()
        mock_settings.stripe_webhook_secret.get_secret_value.return_value = "whsec_test"
        mock_settings.stripe_price_shield_monthly = "price_shield_test"
        mock_settings.stripe_price_pro_monthly = None

        response = await auth_client.post(
            "/api/v1/webhooks/stripe",
            content=b"{}",
            headers={"stripe-signature": "t=1,v1=sig"},
        )

    assert response.status_code == 200
    await db_session.refresh(user)
    assert user.tier == "core"
    assert user.stripe_subscription_id is None


@pytest.mark.asyncio
async def test_payment_failed_logs_and_does_not_downgrade(
    auth_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """invoice.payment_failed does not change user tier."""
    user = auth_client.test_user  # type: ignore[attr-defined]
    stripe_customer_id = f"cus_{uuid.uuid4().hex}"

    user.stripe_customer_id = stripe_customer_id
    user.tier = "pro"
    db_session.add(user)
    await db_session.commit()

    event_data = {"customer": stripe_customer_id, "amount_due": 1999}
    mock_event = _make_stripe_event("invoice.payment_failed", event_data)

    with (
        patch("stripe.Webhook.construct_event", return_value=mock_event),
        patch("backend.app.billing.webhooks.settings") as mock_settings,
    ):
        mock_settings.stripe_webhook_secret = MagicMock()
        mock_settings.stripe_webhook_secret.get_secret_value.return_value = "whsec_test"
        mock_settings.stripe_price_shield_monthly = None
        mock_settings.stripe_price_pro_monthly = None

        response = await auth_client.post(
            "/api/v1/webhooks/stripe",
            content=b"{}",
            headers={"stripe-signature": "t=1,v1=sig"},
        )

    assert response.status_code == 200
    await db_session.refresh(user)
    assert user.tier == "pro"  # Unchanged


@pytest.mark.asyncio
async def test_tier_cache_invalidated_after_upgrade(
    auth_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """Subscription update calls load_tier_config.cache_clear()."""
    user = auth_client.test_user  # type: ignore[attr-defined]
    stripe_customer_id = f"cus_{uuid.uuid4().hex}"
    price_id = "price_pro_test"

    user.stripe_customer_id = stripe_customer_id
    db_session.add(user)
    await db_session.commit()

    event_data = {
        "id": "sub_new",
        "customer": stripe_customer_id,
        "items": {"data": [{"price": {"id": price_id}}]},
    }
    mock_event = _make_stripe_event("customer.subscription.updated", event_data)

    with (
        patch("stripe.Webhook.construct_event", return_value=mock_event),
        patch("backend.app.billing.webhooks.settings") as mock_settings,
        patch.object(load_tier_config, "cache_clear") as mock_cache_clear,
    ):
        mock_settings.stripe_webhook_secret = MagicMock()
        mock_settings.stripe_webhook_secret.get_secret_value.return_value = "whsec_test"
        mock_settings.stripe_price_shield_monthly = None
        mock_settings.stripe_price_pro_monthly = price_id

        await auth_client.post(
            "/api/v1/webhooks/stripe",
            content=b"{}",
            headers={"stripe-signature": "t=1,v1=sig"},
        )

    mock_cache_clear.assert_called_once()


# ─── Billing Endpoints ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_checkout_requires_authentication(
    client: AsyncClient,
) -> None:
    """POST /billing/checkout/{tier} returns 401 without a token."""
    response = await client.post("/api/v1/billing/checkout/shield")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_checkout_rejects_unknown_tier(
    auth_client: AsyncClient,
) -> None:
    """POST /billing/checkout/unknown_tier returns 400."""
    response = await auth_client.post("/api/v1/billing/checkout/unknown_tier")
    assert response.status_code == 400
    assert "Unknown tier" in response.json()["detail"]


@pytest.mark.asyncio
async def test_portal_requires_stripe_customer(
    auth_client: AsyncClient,
) -> None:
    """POST /billing/portal returns 400 when user has no stripe_customer_id."""
    # Default test user has no stripe_customer_id
    response = await auth_client.post("/api/v1/billing/portal")
    assert response.status_code == 400
    assert "No billing account" in response.json()["detail"]
