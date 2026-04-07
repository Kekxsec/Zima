# backend/app/billing/service.py
import asyncio
import uuid

import stripe

from backend.app.core.config import settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

if settings.stripe_secret_key:
    stripe.api_key = settings.stripe_secret_key.get_secret_value()


TIER_TO_PRICE: dict[str, str | None] = {
    "core": None,  # Free
    "plus": settings.stripe_price_shield_monthly,
    "shield": settings.stripe_price_shield_monthly,  # legacy alias
    "pro": settings.stripe_price_pro_monthly,
}


class BillingService:
    async def create_customer(self, user_id: uuid.UUID, email: str) -> str:
        """Creates a Stripe customer and returns the customer ID."""
        customer = await asyncio.to_thread(
            stripe.Customer.create,
            email=email,
            metadata={"zima_user_id": str(user_id)},
        )
        logger.info("billing.customer_created", user_id=str(user_id))
        return customer.id

    async def create_checkout_session(
        self,
        stripe_customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Creates a Stripe Checkout session and returns the URL."""
        session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            customer=stripe_customer_id,
            mode="subscription",
            line_items=[{"price": price_id, "quantity": 1}],
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return session.url

    async def create_portal_session(
        self,
        stripe_customer_id: str,
        return_url: str,
    ) -> str:
        """Creates a Stripe Customer Portal session for managing subscriptions."""
        session = await asyncio.to_thread(
            stripe.billing_portal.Session.create,
            customer=stripe_customer_id,
            return_url=return_url,
        )
        return session.url

    async def cancel_subscription(self, stripe_customer_id: str) -> None:
        """Cancels all active subscriptions for a customer at period end."""
        subscriptions = await asyncio.to_thread(
            stripe.Subscription.list,
            customer=stripe_customer_id,
            status="active",
        )
        for sub in subscriptions.data:
            await asyncio.to_thread(
                stripe.Subscription.modify,
                sub.id,
                cancel_at_period_end=True,
            )
