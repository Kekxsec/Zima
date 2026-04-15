# backend/app/api/v1/billing.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_current_user, get_db_session
from backend.app.auth.models import User
from backend.app.billing.service import TIER_TO_PRICE, BillingService
from backend.app.core.config import settings
from backend.app.db.repositories.assets import AssetRepository
from backend.app.db.repositories.users import UserRepository

router = APIRouter(prefix="/billing", tags=["billing"])


async def get_billing_service() -> BillingService:
    return BillingService()


async def _ensure_stripe_customer(
    user: User,
    billing_service: BillingService,
    db: AsyncSession,
) -> str:
    """
    Returns the user's Stripe customer ID, creating one if it doesn't exist yet.
    Persists the new customer ID to the User row and commits.
    Raises HTTP 400 if the user has no primary email on record.
    """
    if user.stripe_customer_id:
        return user.stripe_customer_id

    asset_repo = AssetRepository(db)
    primary_email = await asset_repo.get_primary_email(user.id)
    if primary_email is None:
        raise HTTPException(
            status_code=400,
            detail="No verified email address found — cannot create billing account.",
        )

    customer_id = await billing_service.create_customer(
        user_id=user.id,
        email=primary_email.value,
    )

    user_repo = UserRepository(db)
    await user_repo.update_stripe_customer_id(user.id, customer_id)
    await db.commit()

    return customer_id


@router.get("/status")
async def billing_status(
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Return the current user's billing posture."""
    return {
        "plan": current_user.tier,
        "status": (
            "active"
            if current_user.stripe_subscription_id or current_user.tier != "core"
            else "inactive"
        ),
        "current_period_end": None,
        "cancel_at_period_end": False,
    }


@router.post("/checkout/{tier}")
async def create_checkout(
    tier: str,
    current_user: User = Depends(get_current_user),
    billing_service: BillingService = Depends(get_billing_service),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    price_id = TIER_TO_PRICE.get(tier)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Unknown tier: {tier}")

    stripe_customer_id = await _ensure_stripe_customer(
        current_user,
        billing_service,
        db,
    )

    url = await billing_service.create_checkout_session(
        stripe_customer_id=stripe_customer_id,
        price_id=price_id,
        success_url=f"{settings.frontend_base_url}/onboarding/checkout/success",
        cancel_url=f"{settings.frontend_base_url}/onboarding/checkout/failure",
    )
    return {"checkout_url": url, "tier": tier}


@router.post("/portal")
async def billing_portal(
    current_user: User = Depends(get_current_user),
    billing_service: BillingService = Depends(get_billing_service),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    stripe_customer_id = await _ensure_stripe_customer(
        current_user,
        billing_service,
        db,
    )

    url = await billing_service.create_portal_session(
        stripe_customer_id=stripe_customer_id,
        return_url=f"{settings.frontend_base_url}/dashboard",
    )
    return {"portal_url": url}
