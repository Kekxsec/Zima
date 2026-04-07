# backend/app/api/v1/auth.py
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    get_asset_service,
    get_auth_service,
    get_db_session,
)
from backend.app.assets.service import AssetService
from backend.app.auth.blacklist import token_blacklist
from backend.app.auth.schemas import OTPRequest, OTPVerify
from backend.app.auth.service import AuthService
from backend.app.auth.utils import decode_access_token
from backend.app.core.config import settings
from backend.app.core.exceptions import (
    AuthTokenExpiredException,
    AuthTokenInvalidException,
)
from backend.app.core.logging import get_logger
from backend.app.core.rate_limit import get_real_ip, limiter
from backend.app.db.repositories.users import UserRepository
from backend.app.email.service import EmailService

router = APIRouter(prefix="/auth", tags=["auth"])
logger = get_logger(__name__)

# Module-level instance — EmailService is stateless after __init__
_email_service = EmailService()

_COOKIE_NAME = "zima_session"


@router.post("/otp/request", status_code=202)
@limiter.limit("3/15minutes")
async def request_otp(
    request: Request,
    body: OTPRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    """
    Requests a sign-in OTP for the given email.

    Always returns HTTP 202 with the same response body regardless of:
    - Whether the email has an account
    - Whether rate limiting has triggered internally
    - Whether the email send succeeds or fails

    This prevents account enumeration attacks.
    """
    client_ip = get_real_ip(request)
    raw_code = await auth_service.request_otp(
        email=str(body.email),
        requesting_ip=client_ip,
        privacy_policy_accepted=body.privacy_policy_accepted,
    )
    if raw_code is not None:
        if not settings.is_production:
            logger.info(
                "auth.dev_otp",
                email=str(body.email),
                raw_code=raw_code,
            )
        await _email_service.send_otp(str(body.email), raw_code)

    return {"message": "If that address is valid, a sign-in code is on its way."}


@router.post("/otp/verify", status_code=200)
@limiter.limit("10/15minutes")
async def verify_otp(
    request: Request,
    response: Response,
    body: OTPVerify,
    auth_service: AuthService = Depends(get_auth_service),
    asset_service: AssetService = Depends(get_asset_service),
) -> dict[str, str]:
    """
    Verifies a submitted OTP code and sets a session cookie.

    On success:
    - Sets httpOnly session cookie containing the JWT
    - Registers the email as a verified, scannable asset

    Returns HTTP 401 for ALL failure modes with an identical response body.
    Does not distinguish between wrong code, expired code, or unknown email.
    """
    try:
        user, token = await auth_service.verify_otp(
            email=str(body.email),
            code=body.code,
        )
    except (AuthTokenInvalidException, AuthTokenExpiredException):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired code.",
        ) from None

    # Register email as verified asset — scanning is only permitted after this
    await asset_service.register_verified_email(
        user_id=user.id,
        email=str(body.email),
    )

    response.set_cookie(
        key=_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.is_production,
        samesite="strict" if settings.is_production else "lax",
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )

    return {"message": "Signed in."}


@router.post("/logout", status_code=200)
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """Clears the session cookie.

    No auth required; safe to call when already signed out.
    """
    token = request.cookies.get(_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    if token:
        try:
            payload = decode_access_token(token)
            # Primary revocation: add JTI to Redis blacklist with TTL = remaining
            # token lifetime so the entry expires automatically.
            jti = payload.get("jti")
            exp = payload.get("exp")
            if isinstance(jti, str) and jti and isinstance(exp, datetime):
                await token_blacklist.revoke(jti, exp)
            # Fallback revocation: update session_revoked_at for tokens that
            # predate JTI support or when Redis is unavailable.
            user = await UserRepository(db).get_active_by_id(str(payload["sub"]))
            if user is not None:
                issued_at = payload.get("iat")
                user.session_revoked_at = (
                    issued_at if isinstance(issued_at, datetime) else datetime.now(UTC)
                )
                await db.commit()
        except (TypeError, ValueError):
            pass

    response.delete_cookie(key=_COOKIE_NAME, path="/")
    return {"message": "Signed out."}
