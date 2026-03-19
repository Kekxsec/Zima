# backend/app/api/dependencies.py
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.assets.service import AssetService
from backend.app.auth.models import User
from backend.app.auth.service import AuthService
from backend.app.auth.utils import decode_access_token
from backend.app.db.repositories.assets import AssetRepository
from backend.app.db.repositories.audit import AuditRepository
from backend.app.db.repositories.auth_tokens import AuthTokenRepository
from backend.app.db.repositories.users import UserRepository
from backend.app.db.session import get_db_session

__all__ = [
    "get_current_user",
    "get_auth_service",
    "get_asset_service",
    "get_db_session",
]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/otp/verify")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
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
