# backend/app/api/v1/billing.py
from fastapi import APIRouter, Depends, HTTPException

from backend.app.api.dependencies import get_current_user
from backend.app.auth.models import User
from backend.app.billing.service import TIER_TO_PRICE, BillingService
from backend.app.core.config import settings

router = APIRouter(prefix="/billing", tags=["billing"])


async def get_billing_service() -> BillingService:
    return BillingService()


@router.post("/checkout/{tier}")
async def create_checkout(
    tier: str,
    current_user: User = Depends(get_current_user),
    billing_service: BillingService = Depends(get_billing_service),
) -> dict[str, str]:
    price_id = TIER_TO_PRICE.get(tier)
    if not price_id:
        raise HTTPException(status_code=400, detail=f"Unknown tier: {tier}")

    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found")

    url = await billing_service.create_checkout_session(
        stripe_customer_id=current_user.stripe_customer_id,
        price_id=price_id,
        success_url=f"{settings.frontend_base_url}/dashboard?upgrade=success",
        cancel_url=f"{settings.frontend_base_url}/dashboard",
    )
    return {"checkout_url": url}


@router.post("/portal")
async def billing_portal(
    current_user: User = Depends(get_current_user),
    billing_service: BillingService = Depends(get_billing_service),
) -> dict[str, str]:
    if not current_user.stripe_customer_id:
        raise HTTPException(status_code=400, detail="No billing account found")

    url = await billing_service.create_portal_session(
        stripe_customer_id=current_user.stripe_customer_id,
        return_url=f"{settings.frontend_base_url}/dashboard",
    )
    return {"portal_url": url}
