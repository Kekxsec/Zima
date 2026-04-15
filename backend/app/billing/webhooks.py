# backend/app/billing/webhooks.py
import ipaddress
from typing import Any

import stripe
from fastapi import APIRouter, HTTPException, Request

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.core.rate_limit import get_real_ip
from backend.app.db.repositories.users import UserRepository
from backend.app.db.session import AsyncSessionLocal
from backend.app.tiers.loader import load_tier_config

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = get_logger(__name__)

# Stripe's published webhook delivery IP ranges.
# Source: https://stripe.com/docs/ips (verified 2026-04)
# Signature verification is the primary security control; IP filtering is
# defence-in-depth only.  Update this list when Stripe publishes new ranges.
_STRIPE_WEBHOOK_IPS: frozenset[str] = frozenset(
    [
        "3.18.12.63",
        "3.130.192.231",
        "13.235.14.237",
        "13.235.122.149",
        "18.211.135.69",
        "35.154.171.200",
        "52.15.183.38",
        "54.88.130.119",
        "54.88.130.237",
        "54.187.174.169",
        "54.187.205.235",
        "54.187.216.72",
    ]
)


def _is_stripe_ip(request: Request) -> bool:
    """Returns True if the request appears to come from a known Stripe IP."""
    client_ip = get_real_ip(request)
    try:
        addr = ipaddress.ip_address(client_ip)
        return str(addr) in _STRIPE_WEBHOOK_IPS
    except ValueError:
        return False


def _build_price_to_tier_map() -> dict[str, str]:
    mapping: dict[str, str] = {}
    if settings.stripe_price_shield_monthly:
        mapping[settings.stripe_price_shield_monthly] = "plus"
    if settings.stripe_price_pro_monthly:
        mapping[settings.stripe_price_pro_monthly] = "pro"
    return mapping


@router.post("/stripe")
async def stripe_webhook(request: Request) -> dict[str, bool]:
    """
    Handles Stripe events that affect user tier.
    Signature verification ensures the event genuinely came from Stripe.
    """
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    # Defence-in-depth: reject requests that don't come from a known Stripe IP.
    # Signature verification below is the primary security control.
    if not _is_stripe_ip(request):
        logger.warning(
            "security.webhook.unexpected_source_ip",
            ip=get_real_ip(request),
        )
        raise HTTPException(status_code=400, detail="Forbidden source IP")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]
            payload,
            sig_header,
            settings.stripe_webhook_secret.get_secret_value(),
        )
    except (stripe.error.SignatureVerificationError, ValueError) as exc:
        logger.warning("webhook.invalid_signature", error=str(exc))
        raise HTTPException(status_code=400, detail="Invalid signature") from exc

    price_to_tier = _build_price_to_tier_map()

    if event["type"] == "customer.subscription.updated":
        await _handle_subscription_updated(event["data"]["object"], price_to_tier)

    elif event["type"] == "customer.subscription.deleted":
        await _handle_subscription_deleted(event["data"]["object"])

    elif event["type"] == "invoice.payment_failed":
        await _handle_payment_failed(event["data"]["object"])

    return {"received": True}


async def _handle_subscription_updated(
    subscription: dict[str, Any], price_to_tier: dict[str, str]
) -> None:
    price_id = subscription["items"]["data"][0]["price"]["id"]
    new_tier = price_to_tier.get(price_id, "core")
    stripe_customer_id = subscription["customer"]

    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        await repo.update_tier_by_stripe_customer_id(
            stripe_customer_id=stripe_customer_id,
            tier=new_tier,
            stripe_subscription_id=subscription["id"],
        )
        await session.commit()

    # Invalidate tier config cache so the next scan uses the new tier
    load_tier_config.cache_clear()
    logger.info("billing.tier_updated", tier=new_tier, customer=stripe_customer_id)


async def _handle_subscription_deleted(subscription: dict[str, Any]) -> None:
    """Subscription cancelled — downgrade to core (free)."""
    stripe_customer_id = subscription["customer"]

    async with AsyncSessionLocal() as session:
        repo = UserRepository(session)
        await repo.update_tier_by_stripe_customer_id(
            stripe_customer_id=stripe_customer_id,
            tier="core",
            stripe_subscription_id=None,
        )
        await session.commit()

    load_tier_config.cache_clear()
    logger.info("billing.downgraded_to_core", customer=stripe_customer_id)


async def _handle_payment_failed(invoice: dict[str, Any]) -> None:
    """Payment failed — log for monitoring. Stripe handles dunning automatically."""
    logger.warning(
        "billing.payment_failed",
        customer=invoice.get("customer"),
        amount=invoice.get("amount_due"),
    )
