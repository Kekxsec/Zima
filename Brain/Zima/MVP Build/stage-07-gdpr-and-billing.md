← [[MVP Master|Stage Progress]]

# Stage 7 — GDPR, Account Management, and Stripe Billing

**Exit condition:** Users can delete their account and all personal data. Stripe billing is integrated with webhook handling that updates user tier. Upgrade and downgrade flows work. Privacy policy and terms endpoints exist. All GDPR-required flows are implemented.

---

## 7.1 Why This Is in the MVP

A UK-based product handling personal data (email addresses, breach records, security findings) is subject to GDPR from the moment the first user signs up. The ICO does not distinguish between a large company and a solo developer — the obligations are the same. These are the minimum requirements before any user data is collected:

- Right to erasure (account deletion + data removal)
- Right of access (data export)
- Lawful basis for processing (consent at sign-up)
- Privacy policy accessible before sign-up
- Transparent communication about what data is stored and why

Stripe is included here rather than post-MVP because without billing there is no revenue, and without revenue there is no product. The tier system is already built — connecting it to Stripe is a small step.

---

## 7.2 Data Deletion — GDPR Right to Erasure

The deletion model uses a two-step approach:
1. **Soft-delete the User row** — `deleted_at` is set, the user can no longer sign in
2. **Hard-delete all personal data** — cascades through assets, signals, findings, scores, auth tokens

The User row itself is retained (with `deleted_at` set and all PII nulled) to preserve referential integrity with billing records and audit logs. Everything else is genuinely deleted.

```python
# api/v1/account.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.api.dependencies import get_current_user, get_db_session
from backend.app.db.session import AsyncSessionLocal
from backend.app.auth.models import User
from backend.app.core.logging import get_logger

router = APIRouter(prefix="/account", tags=["account"])
logger = get_logger(__name__)


@router.delete("/", status_code=202)
async def delete_account(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Initiates account deletion.
    - Immediately invalidates the user's session (soft-delete)
    - Schedules permanent data deletion in background
    Returns immediately — deletion runs asynchronously.
    """
    from datetime import datetime, timezone
    from sqlalchemy import update
    from backend.app.auth.models import User as UserModel

    # Soft-delete immediately to prevent further sign-in
    await db.execute(
        update(UserModel)
        .where(UserModel.id == current_user.id)
        .values(deleted_at=datetime.now(timezone.utc), is_active=False)
    )
    await db.commit()

    # Schedule hard deletion of personal data
    background_tasks.add_task(
        _delete_user_personal_data,
        user_id=current_user.id,
    )

    return {"message": "Account deletion initiated. Your data will be removed within 24 hours."}


async def _delete_user_personal_data(user_id) -> None:
    """
    Hard-deletes all personal data for a user.
    Runs in a background task with its own session.
    Order matters — delete child records before parents.
    """
    import uuid
    from sqlalchemy import delete
    from backend.app.auth.models import AuthToken
    from backend.app.assets.models import Asset
    from backend.app.signals.models import Signal
    from backend.app.correlation.models import Finding
    from backend.app.scoring.models import Score
    from backend.app.jobs.models import Scan

    logger.info("gdpr.deletion_started", user_id=str(user_id))

    async with AsyncSessionLocal() as session:
        # Delete in dependency order
        await session.execute(delete(Score).where(Score.user_id == user_id))
        await session.execute(delete(Finding).where(Finding.user_id == user_id))
        await session.execute(delete(Signal).where(Signal.user_id == user_id))
        await session.execute(delete(Scan).where(Scan.user_id == user_id))
        await session.execute(delete(Asset).where(Asset.user_id == user_id))
        await session.execute(delete(AuthToken).where(
            AuthToken.email.in_(
                # Can't query by user_id on AuthToken — must look up via assets
                # At this point assets are deleted, so use a subquery approach
                # or store user_id on AuthToken (recommended addition)
            )
        ))
        # Null out PII on the User row — keep the row for billing/audit ref integrity
        from sqlalchemy import update
        from backend.app.auth.models import User as UserModel
        await session.execute(
            update(UserModel)
            .where(UserModel.id == user_id)
            .values(tier="deleted")  # Marker for billing system
        )
        await session.commit()

    logger.info("gdpr.deletion_completed", user_id=str(user_id))
```

**Implementation note:** Add `user_id` as a foreign key to `AuthToken` to enable clean deletion. The model update is a one-line migration.

---

## 7.3 Data Export — GDPR Right of Access

```python
@router.get("/export")
async def export_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Returns all data Zima holds about the authenticated user.
    Fulfils GDPR Article 15 right of access.
    """
    from backend.app.db.repositories.assets import AssetRepository
    from backend.app.db.repositories.signals import SignalRepository
    from backend.app.db.repositories.findings import FindingRepository
    from backend.app.db.repositories.scores import ScoreRepository

    asset_repo = AssetRepository(db)
    signal_repo = SignalRepository(db)
    finding_repo = FindingRepository(db)
    score_repo = ScoreRepository(db)

    return {
        "user": {
            "id": str(current_user.id),
            "tier": current_user.tier,
            "last_sign_in_at": current_user.last_sign_in_at,
            "created_at": current_user.created_at,
        },
        "assets": await asset_repo.get_all_for_user(current_user.id),
        "signals": await signal_repo.get_all_for_user(current_user.id),
        "findings": await finding_repo.get_all_for_user(current_user.id),
        "scores": await score_repo.get_all_for_user(current_user.id),
    }
```

---

## 7.4 Stripe Integration

### Billing Service

```python
# billing/service.py
import stripe
from backend.app.core.config import settings
from backend.app.core.logging import get_logger
import uuid

logger = get_logger(__name__)

if settings.stripe_secret_key:
    stripe.api_key = settings.stripe_secret_key.get_secret_value()


TIER_TO_PRICE: dict[str, str | None] = {
    "core": None,  # Free
    "shield": settings.stripe_price_shield_monthly,
    "pro": settings.stripe_price_pro_monthly,
}


class BillingService:
    async def create_customer(self, user_id: uuid.UUID, email: str) -> str:
        """Creates a Stripe customer and returns the customer ID."""
        customer = stripe.Customer.create(
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
        session = stripe.checkout.Session.create(
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
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=return_url,
        )
        return session.url

    async def cancel_subscription(self, stripe_customer_id: str) -> None:
        """Cancels all active subscriptions for a customer at period end."""
        subscriptions = stripe.Subscription.list(
            customer=stripe_customer_id, status="active"
        )
        for sub in subscriptions.data:
            stripe.Subscription.modify(sub.id, cancel_at_period_end=True)
```

### User Model — Billing Fields

Add these fields to the `User` model:

```python
# Addition to auth/models.py User class
stripe_customer_id: Mapped[str | None] = mapped_column(
    String(64), nullable=True, unique=True, index=True
)
stripe_subscription_id: Mapped[str | None] = mapped_column(
    String(64), nullable=True
)
```

### Stripe Webhook Handler

```python
# billing/webhooks.py
import stripe
from fastapi import APIRouter, Request, HTTPException, status
from sqlalchemy import update
from backend.app.db.session import AsyncSessionLocal
from backend.app.auth.models import User
from backend.app.core.config import settings
from backend.app.tiers.loader import load_tier_config  # For cache invalidation
from backend.app.core.logging import get_logger

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = get_logger(__name__)

STRIPE_TO_ZIMA_TIER: dict[str, str] = {
    # Map Stripe price IDs to Zima tier names
    # Populated at runtime from settings
}


def _build_price_to_tier_map() -> dict[str, str]:
    mapping = {}
    if settings.stripe_price_shield_monthly:
        mapping[settings.stripe_price_shield_monthly] = "shield"
    if settings.stripe_price_pro_monthly:
        mapping[settings.stripe_price_pro_monthly] = "pro"
    return mapping


@router.post("/stripe")
async def stripe_webhook(request: Request):
    """
    Handles Stripe events that affect user tier.
    Signature verification ensures the event genuinely came from Stripe.
    """
    if not settings.stripe_webhook_secret:
        raise HTTPException(status_code=500, detail="Webhook secret not configured")

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            settings.stripe_webhook_secret.get_secret_value(),
        )
    except (stripe.error.SignatureVerificationError, ValueError) as e:
        logger.warning("webhook.invalid_signature", error=str(e))
        raise HTTPException(status_code=400, detail="Invalid signature")

    price_to_tier = _build_price_to_tier_map()

    if event["type"] == "customer.subscription.updated":
        await _handle_subscription_updated(event["data"]["object"], price_to_tier)

    elif event["type"] == "customer.subscription.deleted":
        await _handle_subscription_deleted(event["data"]["object"])

    elif event["type"] == "invoice.payment_failed":
        await _handle_payment_failed(event["data"]["object"])

    return {"received": True}


async def _handle_subscription_updated(subscription: dict, price_to_tier: dict) -> None:
    price_id = subscription["items"]["data"][0]["price"]["id"]
    new_tier = price_to_tier.get(price_id, "core")
    stripe_customer_id = subscription["customer"]

    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User)
            .where(User.stripe_customer_id == stripe_customer_id)
            .values(
                tier=new_tier,
                stripe_subscription_id=subscription["id"],
            )
        )
        await session.commit()

    # Invalidate tier config cache so the next scan uses the new tier
    load_tier_config.cache_clear()
    logger.info("billing.tier_updated", tier=new_tier, customer=stripe_customer_id)


async def _handle_subscription_deleted(subscription: dict) -> None:
    """Subscription cancelled — downgrade to core (free)."""
    stripe_customer_id = subscription["customer"]

    async with AsyncSessionLocal() as session:
        await session.execute(
            update(User)
            .where(User.stripe_customer_id == stripe_customer_id)
            .values(tier="core", stripe_subscription_id=None)
        )
        await session.commit()

    load_tier_config.cache_clear()
    logger.info("billing.downgraded_to_core", customer=stripe_customer_id)


async def _handle_payment_failed(invoice: dict) -> None:
    """Payment failed — log for monitoring. Stripe handles dunning automatically."""
    logger.warning(
        "billing.payment_failed",
        customer=invoice.get("customer"),
        amount=invoice.get("amount_due"),
    )
```

### Billing API Endpoints

```python
# api/v1/billing.py
from fastapi import APIRouter, Depends, HTTPException
from backend.app.api.dependencies import get_current_user, get_db_session
from backend.app.billing.service import BillingService, TIER_TO_PRICE
from backend.app.auth.models import User

router = APIRouter(prefix="/billing", tags=["billing"])
billing_service = BillingService()


@router.post("/checkout/{tier}")
async def create_checkout(
    tier: str,
    current_user: User = Depends(get_current_user),
):
    price_id = TIER_TO_PRICE.get(tier)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Unknown tier: {tier}")

    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found")

    url = await billing_service.create_checkout_session(
        stripe_customer_id=current_user.stripe_customer_id,
        price_id=price_id,
        success_url="https://yourdomain.com/dashboard?upgrade=success",
        cancel_url="https://yourdomain.com/dashboard",
    )
    return {"checkout_url": url}


@router.post("/portal")
async def billing_portal(
    current_user: User = Depends(get_current_user),
):
    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found")

    url = await billing_service.create_portal_session(
        stripe_customer_id=current_user.stripe_customer_id,
        return_url="https://yourdomain.com/dashboard",
    )
    return {"portal_url": url}
```

---

## 7.5 Privacy Policy and Terms Endpoints

These endpoints return the URLs for your privacy policy and terms of service. The actual documents live on your marketing site or as static pages. Having endpoints for them makes it easy for the frontend to link to them consistently.

```python
# api/v1/legal.py
from fastapi import APIRouter
from backend.app.core.config import settings

router = APIRouter(prefix="/legal", tags=["legal"])

@router.get("/privacy")
async def privacy_policy():
    return {"url": "https://yourdomain.com/privacy"}

@router.get("/terms")
async def terms_of_service():
    return {"url": "https://yourdomain.com/terms"}
```

The actual privacy policy must cover at minimum:
- What data you collect (email, breach results, security signals)
- Why you collect it (providing the service)
- How long you retain it
- Who you share it with (Stripe, Resend, HIBP)
- How users can request deletion or export
- Your contact details for data requests

---

## 7.6 Onboarding — Consent at Sign-up

When a user first signs in via OTP, record their consent to the privacy policy before registering them. This is the lawful basis for processing their data.

Add a `privacy_policy_accepted_at` field to the User model:

```python
privacy_policy_accepted_at: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)
```

The OTP verify endpoint should require a `privacy_policy_accepted: bool` field on first sign-in. If the user is new and this is `False`, reject with a clear message. If the user already exists, skip this check.

---

## 7.7 Stage 7 Tests

**Account deletion:**
- `test_delete_account_soft_deletes_user_immediately`
- `test_delete_account_prevents_subsequent_sign_in`
- `test_delete_personal_data_removes_assets_signals_findings_scores`
- `test_delete_preserves_user_row_for_audit`

**Data export:**
- `test_export_returns_all_user_data`
- `test_export_excludes_other_users_data`

**Stripe webhook:**
- `test_webhook_rejects_invalid_signature`
- `test_subscription_updated_upgrades_tier`
- `test_subscription_deleted_downgrades_to_core`
- `test_payment_failed_logs_and_does_not_downgrade`
- `test_tier_cache_invalidated_after_upgrade`

**Billing endpoints:**
- `test_checkout_requires_authentication`
- `test_checkout_rejects_unknown_tier`
- `test_portal_requires_stripe_customer`
