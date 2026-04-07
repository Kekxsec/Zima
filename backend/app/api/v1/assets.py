# backend/app/api/v1/assets.py
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field

from backend.app.api.dependencies import (
    get_asset_service,
    get_auth_service,
    get_current_user,
)
from backend.app.assets.service import AssetService
from backend.app.auth.models import User
from backend.app.auth.service import AuthService
from backend.app.core.config import settings
from backend.app.core.enums import EntityType
from backend.app.core.logging import get_logger
from backend.app.core.rate_limit import get_real_ip, limiter
from backend.app.email.service import EmailService

router = APIRouter(prefix="/assets", tags=["assets"])
logger = get_logger(__name__)

# Entity types a user can declare via this endpoint.
# EMAIL and PHONE_NUMBER assets require OTP verification.
# USERNAME assets may be stored as user-declared inventory but are not marked
# verified automatically.
_DECLARABLE_TYPES = {EntityType.USERNAME}

_email_service = EmailService()


class AssetDeclarePayload(BaseModel):
    entity_type: EntityType
    value: str


class AssetOut(BaseModel):
    asset_id: str
    entity_type: str
    value: str
    is_verified: bool
    created_at: datetime


class EmailOTPRequest(BaseModel):
    email: EmailStr


class EmailOTPVerify(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class PhoneOTPRequest(BaseModel):
    phone: str


class PhoneOTPVerify(BaseModel):
    phone: str
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


@router.post("", response_model=AssetOut, status_code=status.HTTP_201_CREATED)
async def declare_asset(
    payload: AssetDeclarePayload,
    current_user: User = Depends(get_current_user),
    asset_service: AssetService = Depends(get_asset_service),
) -> AssetOut:
    """Register a username asset for the current user.

    User-declared assets stored via this endpoint are inventory only and are
    not marked verified automatically.
    """
    if payload.entity_type not in _DECLARABLE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Entity type '{payload.entity_type}' cannot be declared via this "
                "endpoint."
            ),
        )

    value = payload.value.strip().lower()
    if not value:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Asset value must not be empty.",
        )

    asset = await asset_service.register_declared_asset(
        user_id=current_user.id,
        entity_type=str(payload.entity_type),
        value=value,
    )

    return AssetOut(
        asset_id=str(asset.id),
        entity_type=asset.entity_type,
        value=asset.value,
        is_verified=asset.is_verified,
        created_at=asset.created_at
        if asset.created_at.tzinfo
        else asset.created_at.replace(tzinfo=UTC),
    )


@router.post("/email/otp/request", status_code=202)
@limiter.limit("3/15minutes")
async def request_email_asset_otp(
    request: Request,
    body: EmailOTPRequest,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    """Request an OTP to verify an additional email address.

    Always returns 202 regardless of whether the email is already registered
    or rate-limiting has triggered, to prevent enumeration.
    """
    email = str(body.email).lower().strip()
    client_ip = get_real_ip(request)
    raw_code = await auth_service.request_asset_email_otp(
        email,
        client_ip,
        current_user,
    )
    if raw_code is not None:
        if not settings.is_production:
            logger.info(
                "assets.dev_email_otp",
                email=email,
                raw_code=raw_code,
            )
        await _email_service.send_otp(email, raw_code)
    return {
        "message": "If that address is reachable, a verification code is on its way."
    }


@router.post("/phone/otp/request", status_code=202)
@limiter.limit("3/15minutes")
async def request_phone_asset_otp(
    request: Request,
    body: PhoneOTPRequest,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    """Request an OTP to verify a phone number asset.

    In dev mode the code is printed to the backend console.
    In production this endpoint would trigger an SMS send.
    Always returns 202 to prevent enumeration.
    """
    phone = body.phone.strip()
    client_ip = get_real_ip(request)
    raw_code = await auth_service.request_asset_phone_otp(
        phone,
        client_ip,
        current_user,
    )
    if raw_code is not None:
        if not settings.is_production:
            logger.info(
                "assets.dev_phone_otp",
                phone=phone,
                raw_code=raw_code,
            )
        # TODO: replace with SMS delivery (e.g. Twilio) when available
    return {
        "message": "If that number is reachable, a verification code is on its way."
    }


@router.post("/phone/otp/verify", response_model=AssetOut, status_code=200)
@limiter.limit("10/15minutes")
async def verify_phone_asset_otp(
    request: Request,
    body: PhoneOTPVerify,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    asset_service: AssetService = Depends(get_asset_service),
) -> AssetOut:
    """Verify a phone OTP and register the number as a verified asset."""
    phone = body.phone.strip()
    success = await auth_service.verify_asset_phone_otp(
        phone,
        body.code,
        current_user,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired code.",
        )
    asset = await asset_service.register_verified_asset(
        user_id=current_user.id,
        entity_type="phone_number",
        value=phone,
    )
    return AssetOut(
        asset_id=str(asset.id),
        entity_type=asset.entity_type,
        value=asset.value,
        is_verified=asset.is_verified,
        created_at=asset.created_at
        if asset.created_at.tzinfo
        else asset.created_at.replace(tzinfo=UTC),
    )


@router.post("/email/otp/verify", response_model=AssetOut, status_code=200)
@limiter.limit("10/15minutes")
async def verify_email_asset_otp(
    request: Request,
    body: EmailOTPVerify,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    asset_service: AssetService = Depends(get_asset_service),
) -> AssetOut:
    """Verify an OTP code and register the email as a verified asset.

    On success the email is added to the user's asset list and is eligible
    for future scans. Returns 401 for invalid or expired codes.
    """
    email = str(body.email).lower().strip()
    success = await auth_service.verify_asset_email_otp(
        email,
        body.code,
        current_user,
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired code.",
        )
    asset = await asset_service.register_verified_email(
        user_id=current_user.id,
        email=email,
    )
    return AssetOut(
        asset_id=str(asset.id),
        entity_type=asset.entity_type,
        value=asset.value,
        is_verified=asset.is_verified,
        created_at=asset.created_at
        if asset.created_at.tzinfo
        else asset.created_at.replace(tzinfo=UTC),
    )
