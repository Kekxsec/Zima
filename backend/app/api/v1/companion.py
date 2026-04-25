# backend/app/api/v1/companion.py
"""
Companion binary API — four endpoints:

  POST /companion/setup-token   User browser → generate 15-min setup token
  POST /companion/register      Companion binary → exchange token for JWT
  POST /companion/snapshot      Companion binary → submit browser/OS snapshot
  GET  /companion/status        User browser → check connection state
"""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    get_companion_user,
    get_current_user,
    get_db_session,
)
from backend.app.auth.models import AuthToken, User
from backend.app.auth.service import match_token
from backend.app.auth.utils import create_companion_token
from backend.app.core.config import settings
from backend.app.core.crypto import encrypt_field
from backend.app.core.rate_limit import limiter
from backend.app.db.repositories.auth_tokens import AuthTokenRepository
from backend.app.db.repositories.companion import CompanionRepository

router = APIRouter(prefix="/companion", tags=["companion"])


# ─── Schemas ─────────────────────────────────────────────────────────────────


class SetupTokenResponse(BaseModel):
    setup_token: str
    expires_in: int  # seconds
    user_id: str  # UUID of the authenticated user — needed for the setup command


class RegisterRequest(BaseModel):
    setup_token: str
    user_id: uuid.UUID
    machine_id: str  # SHA-256 of stable hardware identifier
    platform: str  # "darwin" | "linux" | "windows"
    version: str  # semver e.g. "0.1.0"


class RegisterResponse(BaseModel):
    companion_token: str


class SnapshotRequest(BaseModel):
    raw_snapshot: dict[str, object]


class CompanionStatusResponse(BaseModel):
    connected: bool
    last_seen_at: str | None
    platform: str | None
    version: str | None
    extension_count: int


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.post("/setup-token", response_model=SetupTokenResponse)
async def create_setup_token(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> SetupTokenResponse:
    """
    Generates a one-time setup token for the companion binary.
    The user runs: zima-companion setup --token <token> --backend <url> --user-id <uuid>
    Token expires in 15 minutes.
    """
    raw_token = secrets.token_urlsafe(32)
    code_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    key = f"companion_setup:{current_user.id}"
    expires_at = datetime.now(UTC) + timedelta(
        minutes=settings.companion_setup_token_expire_minutes
    )

    token_repo = AuthTokenRepository(db)
    token = AuthToken(
        email=key,
        code_hash=code_hash,
        expires_at=expires_at,
    )
    await token_repo.create(token)
    await db.commit()

    return SetupTokenResponse(
        setup_token=raw_token,
        expires_in=settings.companion_setup_token_expire_minutes * 60,
        user_id=str(current_user.id),
    )


@router.post("/register", response_model=RegisterResponse)
@limiter.limit("10/hour")
async def register_companion(
    request: Request,  # required by slowapi
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
) -> RegisterResponse:
    """
    Exchanges a setup token for a long-lived companion JWT.
    The companion binary calls this once during `zima-companion setup`.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired setup token.",
    )

    key = f"companion_setup:{body.user_id}"
    code_hash = hashlib.sha256(body.setup_token.encode()).hexdigest()

    token_repo = AuthTokenRepository(db)
    active_tokens = await token_repo.list_active_for_email(key)
    auth_token = match_token(active_tokens, code_hash)
    if auth_token is None:
        raise credentials_exception

    # Mark token as used
    auth_token.used_at = datetime.now(UTC)

    machine_id_encrypted = encrypt_field(body.machine_id)
    jti = str(uuid.uuid4())

    companion_repo = CompanionRepository(db)
    session = await companion_repo.upsert_session(
        user_id=body.user_id,
        machine_id_encrypted=machine_id_encrypted,
        platform=body.platform,
        version=body.version,
        jti=jti,
    )
    await db.commit()

    companion_token = create_companion_token(
        user_id=str(body.user_id),
        session_id=str(session.id),
        jti=jti,
        expire_days=settings.companion_token_expire_days,
    )

    return RegisterResponse(companion_token=companion_token)


@router.post("/snapshot", status_code=202)
async def post_snapshot(
    body: SnapshotRequest,
    current_user: User = Depends(get_companion_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    """
    Accepts a browser/OS snapshot from the companion daemon.
    Called every 5 minutes by `zima-companion run`.
    """
    companion_repo = CompanionRepository(db)
    session = await companion_repo.get_session_by_user(current_user.id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No companion session found for this user.",
        )

    await companion_repo.update_last_seen(session.id)
    await companion_repo.insert_snapshot(
        user_id=current_user.id,
        session_id=session.id,
        raw=body.raw_snapshot,
    )
    await db.commit()

    return {"status": "accepted"}


@router.get("/status", response_model=CompanionStatusResponse)
async def get_companion_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> CompanionStatusResponse:
    """
    Returns connection state for the current user's companion session.
    Polled by the frontend every 30 seconds.
    A session is considered stale if last_seen_at > 10 minutes ago.
    """
    companion_repo = CompanionRepository(db)
    session = await companion_repo.get_session_by_user(current_user.id)

    if session is None:
        return CompanionStatusResponse(
            connected=False,
            last_seen_at=None,
            platform=None,
            version=None,
            extension_count=0,
        )

    stale_threshold = timedelta(minutes=10)
    is_stale = (datetime.now(UTC) - session.last_seen_at) > stale_threshold

    snapshot = await companion_repo.get_latest_snapshot(current_user.id)
    extension_count = 0
    if snapshot is not None:
        raw: dict[str, object] = snapshot.raw_snapshot or {}
        browsers_raw = raw.get("browsers")
        browsers: list[dict[str, object]] = (
            browsers_raw if isinstance(browsers_raw, list) else []
        )
        for browser in browsers:
            exts_raw = browser.get("extensions")
            extensions: list[dict[str, object]] = (
                exts_raw if isinstance(exts_raw, list) else []
            )
            extension_count += len(extensions)

    return CompanionStatusResponse(
        connected=not is_stale,
        last_seen_at=session.last_seen_at.isoformat(),
        platform=session.platform,
        version=session.companion_version,
        extension_count=extension_count,
    )
