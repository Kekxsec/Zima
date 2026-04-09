# backend/app/api/dependencies.py
import uuid
from datetime import datetime

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.assets.service import AssetService
from backend.app.auth.blacklist import token_blacklist
from backend.app.auth.models import User
from backend.app.auth.service import AuthService
from backend.app.auth.utils import decode_access_token, decode_companion_token
from backend.app.db.repositories.assets import AssetRepository
from backend.app.db.repositories.audit import AuditRepository
from backend.app.db.repositories.auth_tokens import AuthTokenRepository
from backend.app.db.repositories.users import UserRepository
from backend.app.db.session import get_db_session

__all__ = [
    "get_current_user",
    "get_companion_user",
    "get_auth_service",
    "get_asset_service",
    "get_db_session",
]

_COOKIE_NAME = "zima_session"


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> User:
    # Cookie-based auth for browser clients; Bearer header fallback for API/Swagger
    token = request.cookies.get(_COOKIE_NAME)
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
    )
    if not token:
        raise credentials_exception

    try:
        payload = decode_access_token(token)
    except ValueError:
        raise credentials_exception from None

    user_repo = UserRepository(db)
    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except (ValueError, KeyError):
        raise credentials_exception from None
    user = await user_repo.get_active_by_id(user_id)

    if not user:
        raise credentials_exception

    # Primary revocation check: JTI blacklist (Redis).
    # Provides immediate, per-token revocation without race conditions.
    jti = payload.get("jti")
    if isinstance(jti, str) and jti:
        if await token_blacklist.is_revoked(jti):
            raise credentials_exception

    # Fallback revocation: timestamp comparison for tokens that predate JTI
    # support or when the Redis blacklist is unavailable.
    issued_at = payload.get("iat")
    if user.session_revoked_at is not None:
        if not isinstance(issued_at, datetime):
            raise credentials_exception
        if issued_at <= user.session_revoked_at:
            raise credentials_exception

    return user


async def get_companion_user(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> "User":
    """
    Authenticates requests from the Rust companion binary.
    Bearer header ONLY — companions are not browsers, no cookie support.
    Validates that the token type is 'companion'.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate companion credentials.",
    )
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise credentials_exception
    token = auth_header[7:]

    try:
        payload = decode_companion_token(token)
    except ValueError:
        raise credentials_exception from None

    user_repo = UserRepository(db)
    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except (ValueError, KeyError):
        raise credentials_exception from None

    user = await user_repo.get_active_by_id(user_id)
    if not user:
        raise credentials_exception

    return user


async def get_auth_service(
    db: AsyncSession = Depends(get_db_session),
) -> AuthService:
    user_repo = UserRepository(db)
    token_repo = AuthTokenRepository(db)
    audit_repo = AuditRepository(db)
    return AuthService(
        session=db,
        user_repo=user_repo,
        token_repo=token_repo,
        audit_repo=audit_repo,
    )


async def get_asset_service(
    db: AsyncSession = Depends(get_db_session),
) -> AssetService:
    asset_repo = AssetRepository(db)
    return AssetService(session=db, asset_repo=asset_repo)
