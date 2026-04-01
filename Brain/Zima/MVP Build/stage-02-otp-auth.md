← [[MVP Master|Stage Progress]]

# Stage 2 — OTP Authentication

**Exit condition:** `uv run pytest tests/unit/auth/ tests/api/test_auth_endpoints.py -v` passes. A user can request an OTP (logged to console in dev), verify it, receive a JWT, and have their email registered as a verified asset. Rate limiting returns 429 after threshold. All failure paths return identical 401 responses.

**Read CLAUDE-CODE-BRIEFING.md before starting this stage.**

---

## Files to Create in This Stage — In Order

1. `backend/app/auth/models.py`
2. `backend/app/db/repositories/auth_tokens.py`
3. `backend/app/db/repositories/users.py` ← defined in CLAUDE-CODE-BRIEFING.md
4. `backend/app/auth/utils.py`
5. `backend/app/auth/schemas.py`
6. `backend/app/auth/service.py`
7. `backend/app/assets/models.py`
8. `backend/app/db/repositories/assets.py` ← defined in CLAUDE-CODE-BRIEFING.md
9. `backend/app/assets/service.py` ← defined in CLAUDE-CODE-BRIEFING.md
10. `backend/app/email/service.py`
11. `backend/app/email/templates/otp.py`
12. `backend/app/api/dependencies.py` ← defined in CLAUDE-CODE-BRIEFING.md
13. `backend/app/api/v1/auth.py`
14. `backend/app/api/router.py` ← defined in CLAUDE-CODE-BRIEFING.md
15. Run: `uv run alembic revision --autogenerate -m "auth_and_assets"`
16. Run: `uv run alembic upgrade head`
17. Write tests

---

## 2.1 Auth Models

```python
# backend/app/auth/models.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tier: Mapped[str] = mapped_column(String(20), default="core", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_sign_in_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Billing fields — populated when Stripe customer is created
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, unique=True, index=True
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )
    # GDPR — consent recorded at first sign-in
    privacy_policy_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class AuthToken(Base):
    """
    One-time sign-in codes. Single-use, 15-minute expiry.
    The raw code is never stored — only its SHA-256 hash.
    Email is stored here (not on User) because a token may exist
    before the User row does (first sign-in creates User on verify, not request).
    """

    __tablename__ = "auth_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    requested_from_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)

    __table_args__ = (
        Index("ix_auth_token_email_hash", "email", "code_hash"),
    )

    @property
    def is_expired(self) -> bool:
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_used(self) -> bool:
        return self.used_at is not None
```

---

## 2.2 Auth Token Repository

```python
# backend/app/db/repositories/auth_tokens.py
from datetime import datetime, timezone

from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.models import AuthToken


class AuthTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_valid_token(
        self, email: str, code_hash: str
    ) -> AuthToken | None:
        """
        Returns a matching token only if it is:
        - Correct email and code_hash
        - Not yet used (used_at IS NULL)
        - Not expired (expires_at > now)
        Returns None for any other condition.
        """
        result = await self.session.execute(
            select(AuthToken)
            .where(
                AuthToken.email == email,
                AuthToken.code_hash == code_hash,
                AuthToken.used_at.is_(None),
                AuthToken.expires_at > datetime.now(timezone.utc),
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def count_active_for_email(self, email: str) -> int:
        """
        Counts tokens for this email that are unused and not yet expired.
        Used to enforce MAX_ACTIVE_TOKENS_PER_EMAIL rate limit.
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(AuthToken)
            .where(
                AuthToken.email == email,
                AuthToken.used_at.is_(None),
                AuthToken.expires_at > datetime.now(timezone.utc),
            )
        )
        return result.scalar_one()

    async def invalidate_all_for_email(self, email: str) -> None:
        """Marks all active tokens for an email as used. Called on account deletion."""
        await self.session.execute(
            update(AuthToken)
            .where(
                AuthToken.email == email,
                AuthToken.used_at.is_(None),
            )
            .values(used_at=datetime.now(timezone.utc))
        )
```

---

## 2.3 User Repository

Create `backend/app/db/repositories/users.py` using the exact implementation in **CLAUDE-CODE-BRIEFING.md** under "db/repositories/users.py — Complete Implementation".

Do not write a different implementation. Copy it exactly.

---

## 2.4 Auth Utils

**JWT library:** Use `PyJWT` (`import jwt`). Do NOT use `python-jose` — it is unmaintained and has known CVEs. `PyJWT` is declared in `pyproject.toml` as `PyJWT>=2.8.0`.

```python
# backend/app/auth/utils.py
from datetime import UTC, datetime, timedelta

import jwt

from backend.app.core.config import settings


def create_access_token(subject: str, tier: str) -> str:
    """
    Creates a signed JWT access token.
    subject: str representation of user UUID
    tier: user's current tier name (e.g. "core", "shield")
    """
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {
        "sub": subject,
        "tier": tier,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, object]:
    """
    Decodes and validates a JWT access token.
    Raises ValueError if the token is invalid, expired, or wrong type.
    Never raises jwt.PyJWTError — always converts to ValueError.
    """
    try:
        payload: dict[str, object] = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "access":
            raise ValueError("Token type is not 'access'")
        return payload
    except jwt.PyJWTError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc
```

---

## 2.5 Auth Schemas

```python
# backend/app/auth/schemas.py
from pydantic import BaseModel, EmailStr, Field


class OTPRequest(BaseModel):
    email: EmailStr
    # Required on first sign-in. Ignored for returning users.
    # The endpoint checks this only when creating a new user.
    privacy_policy_accepted: bool = False


class OTPVerify(BaseModel):
    email: EmailStr
    # Exactly 6 numeric digits. Rejects non-numeric and wrong-length codes
    # before any database query runs.
    code: str = Field(..., min_length=6, max_length=6, pattern=r"^\d{6}$")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

---

## 2.6 Asset Model

Create `backend/app/assets/models.py`:

```python
# backend/app/assets/models.py
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base, TimestampMixin


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[str] = mapped_column(String(512), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # True only if user has proven ownership via OTP sign-in or explicit verification.
    # Module runner MUST NOT scan assets where is_verified=False.
    # Only AssetService.register_verified_email() sets this to True.
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "entity_type", "value",
            name="uq_asset_user_type_value"
        ),
        Index("ix_asset_user_verified", "user_id", "is_verified"),
        Index("ix_asset_user_primary", "user_id", "is_primary"),
    )
```

---

## 2.7 Asset Repository

Create `backend/app/db/repositories/assets.py` using the exact implementation in **CLAUDE-CODE-BRIEFING.md** under "db/repositories/assets.py — Complete Implementation".

Do not write a different implementation. Copy it exactly.

---

## 2.8 Asset Service

Create `backend/app/assets/service.py` using the exact implementation in **CLAUDE-CODE-BRIEFING.md** under "assets/service.py — Complete Implementation".

Do not write a different implementation. Copy it exactly.

---

## 2.9 Auth Service

**Note:** `AuthService.__init__` requires `audit_repo: AuditRepository`. Wire it via `get_auth_service` in `api/dependencies.py`. Audit events (`SIGN_IN_REQUESTED`, `SIGN_IN_SUCCESS`, `SIGN_IN_FAILED`, `OTP_RATE_LIMITED`) must be emitted on every auth path — including failures — before the session commits.

```python
# backend/app/auth/service.py
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.assets.models import Asset
from backend.app.auth.models import AuthToken, User
from backend.app.core.exceptions import (
    AuthOTPRateLimitException,
    AuthTokenAlreadyUsedException,
    AuthTokenExpiredException,
    AuthTokenInvalidException,
)
from backend.app.core.logging import get_logger
from backend.app.db.repositories.auth_tokens import AuthTokenRepository
from backend.app.db.repositories.users import UserRepository

logger = get_logger(__name__)

OTP_EXPIRY_MINUTES: int = 15
MAX_ACTIVE_TOKENS_PER_EMAIL: int = 3


def _generate_code() -> str:
    """
    Cryptographically secure 6-digit numeric OTP.
    Range: 100000–999999 inclusive.
    Uses secrets.randbelow which is CSPRNG-backed.
    """
    return str(secrets.randbelow(900000) + 100000)


def _hash_code(code: str) -> str:
    """SHA-256 hash of the raw OTP code. Only the hash is stored."""
    return hashlib.sha256(code.encode()).hexdigest()


class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        user_repo: UserRepository,
        token_repo: AuthTokenRepository,
    ) -> None:
        self.session = session
        self.user_repo = user_repo
        self.token_repo = token_repo

    async def request_otp(
        self,
        email: str,
        requesting_ip: str,
        privacy_policy_accepted: bool = False,
    ) -> Optional[str]:
        """
        Generates and stores an OTP for the given email.

        Returns the raw 6-digit code string if successful.
        Returns None silently if rate limit is hit.
        The caller ALWAYS returns the same HTTP response regardless of return value
        to prevent account enumeration.

        Creates a new User row on first ever sign-in for this email.
        """
        email = email.lower().strip()

        active_count = await self.token_repo.count_active_for_email(email)
        if active_count >= MAX_ACTIVE_TOKENS_PER_EMAIL:
            logger.warning("auth.otp_rate_limit", ip=requesting_ip)
            return None

        # Find existing user via their primary email asset
        user = await self.user_repo.get_by_email(email)
        if not user:
            # First sign-in — create user row and a placeholder email asset.
            # The asset is unverified here; AssetService.register_verified_email()
            # marks it verified after OTP confirmation. The asset must exist now
            # so verify_otp can look up the user by email via the Asset join.
            user = User(
                privacy_policy_accepted_at=(
                    datetime.now(timezone.utc) if privacy_policy_accepted else None
                )
            )
            self.session.add(user)
            await self.session.flush()  # Assigns user.id without committing
            asset = Asset(
                user_id=user.id,
                entity_type="email",
                value=email,
                is_primary=True,
                is_verified=False,
            )
            self.session.add(asset)
            logger.info("auth.new_user_created", user_id=str(user.id))

        raw_code = _generate_code()
        token = AuthToken(
            email=email,
            code_hash=_hash_code(raw_code),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES),
            requested_from_ip=requesting_ip,
        )
        self.session.add(token)
        await self.session.commit()

        logger.info("auth.otp_issued", email_domain=email.split("@")[-1])
        return raw_code

    async def verify_otp(
        self, email: str, code: str
    ) -> tuple[User, str]:
        """
        Verifies a submitted OTP code.

        On success:
        - Marks the token as used (prevents replay)
        - Updates user.last_sign_in_at
        - Returns (user, jwt_access_token)

        Raises AuthTokenInvalidException for ALL failure modes (wrong code,
        expired, already used, user not found). This ensures identical
        error responses regardless of failure reason.

        Does NOT register the email as a verified asset — the API endpoint
        does that after this method returns successfully.
        """
        email = email.lower().strip()
        token = await self.token_repo.get_valid_token(email, _hash_code(code))

        # Identical exception for all failure modes — no information leakage
        if not token or token.is_expired or token.is_used:
            logger.warning("auth.otp_verify_failed", email_domain=email.split("@")[-1])
            raise AuthTokenInvalidException("Invalid or expired code.")

        # Consume token before any other operation — prevents concurrent replay
        token.used_at = datetime.now(timezone.utc)
        await self.session.flush()

        user = await self.user_repo.get_by_email(email)
        if not user or user.is_deleted:
            raise AuthTokenInvalidException("Invalid or expired code.")

        user.last_sign_in_at = datetime.now(timezone.utc)
        await self.session.commit()

        from backend.app.auth.utils import create_access_token

        jwt_token = create_access_token(
            subject=str(user.id),
            tier=user.tier,
        )

        logger.info("auth.sign_in_success", user_id=str(user.id))
        return user, jwt_token
```

---

## 2.10 Email Service

```python
# backend/app/email/service.py
from backend.app.core.config import settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)


class EmailService:
    """
    Sends transactional email via Resend.
    Falls back to console logging in development (when RESEND_API_KEY is not set).
    Never raises — email failures are logged but do not break the calling operation.
    """

    def __init__(self) -> None:
        self._configured = settings.resend_api_key is not None
        if self._configured:
            import resend
            resend.api_key = settings.resend_api_key.get_secret_value()  # type: ignore[union-attr]

    async def send_otp(self, to_email: str, code: str) -> None:
        """Sends a sign-in OTP code to the given email address."""
        if not self._configured:
            # Development only — logs code to console for testing
            # This branch MUST NOT execute in production (APP_ENV=production)
            logger.info("email.otp_dev_console", email=to_email, code=code)
            return

        from backend.app.email.templates.otp import otp_html, otp_text
        import resend

        try:
            resend.Emails.send({
                "from": f"{settings.email_from_name} <{settings.email_from_address}>",
                "to": [to_email],
                "subject": "Your Zima sign-in code",
                "html": otp_html(code),
                "text": otp_text(code),
            })
            logger.info("email.otp_sent")
        except Exception as exc:
            # Log but do not raise — token is already stored, user can request another
            logger.error("email.send_failed", error=str(exc))
```

---

## 2.11 OTP Email Template

```python
# backend/app/email/templates/otp.py


def otp_html(code: str) -> str:
    return f"""<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; max-width: 480px; margin: 0 auto; padding: 24px;">
  <h2 style="color: #0f172a; margin-bottom: 8px;">Sign in to Zima</h2>
  <p style="color: #475569; margin-bottom: 24px;">Your sign-in code is:</p>
  <div style="font-size: 36px; font-weight: 700; letter-spacing: 8px;
              padding: 24px; background: #f1f5f9; text-align: center;
              border-radius: 8px; color: #0f172a; margin-bottom: 24px;">
    {code}
  </div>
  <p style="color: #475569; margin-bottom: 8px;">This code expires in 15 minutes.</p>
  <p style="color: #94a3b8; font-size: 13px;">
    If you did not request this code, you can safely ignore this email.
  </p>
</body>
</html>"""


def otp_text(code: str) -> str:
    return (
        f"Your Zima sign-in code is: {code}\n\n"
        f"This code expires in 15 minutes.\n\n"
        f"If you did not request this code, you can safely ignore this email."
    )
```

---

## 2.12 API Dependencies

Create `backend/app/api/dependencies.py` using the exact implementation in **CLAUDE-CODE-BRIEFING.md** under "api/dependencies.py — Complete Implementation".

Do not write a different implementation. Copy it exactly.

---

## 2.13 Auth API Endpoint

```python
# backend/app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException, Request, status

from backend.app.api.dependencies import get_asset_service, get_auth_service
from backend.app.assets.service import AssetService
from backend.app.auth.schemas import OTPRequest, OTPVerify, TokenResponse
from backend.app.auth.service import AuthService
from backend.app.core.exceptions import AuthTokenInvalidException, AuthTokenExpiredException
from backend.app.email.service import EmailService

router = APIRouter(prefix="/auth", tags=["auth"])

# Module-level instance — EmailService is stateless after __init__
_email_service = EmailService()


@router.post("/otp/request", status_code=202)
async def request_otp(
    body: OTPRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    """
    Requests a sign-in OTP for the given email.

    Rate limited: 3 requests per 15 minutes per IP (enforced by slowapi in main.py).

    Always returns HTTP 202 with the same response body regardless of:
    - Whether the email has an account
    - Whether rate limiting has triggered internally
    - Whether the email send succeeds or fails

    This prevents account enumeration attacks.
    """
    client_ip = request.client.host if request.client else "unknown"
    raw_code = await auth_service.request_otp(
        email=str(body.email),
        requesting_ip=client_ip,
        privacy_policy_accepted=body.privacy_policy_accepted,
    )
    if raw_code is not None:
        await _email_service.send_otp(str(body.email), raw_code)

    return {"message": "If that address is valid, a sign-in code is on its way."}


@router.post("/otp/verify", response_model=TokenResponse)
async def verify_otp(
    body: OTPVerify,
    auth_service: AuthService = Depends(get_auth_service),
    asset_service: AssetService = Depends(get_asset_service),
) -> TokenResponse:
    """
    Verifies a submitted OTP code and returns a JWT access token.

    Rate limited: 10 requests per 15 minutes per IP (enforced by slowapi in main.py).

    On success:
    - Returns JWT access token
    - Registers the email as a verified, scannable asset

    Returns HTTP 401 for ALL failure modes with an identical response body.
    Does not distinguish between wrong code, expired code, or unknown email.
    """
    try:
        user, token = await auth_service.verify_otp(
            email=str(body.email),
            code=body.code,
        )
    except (AuthTokenInvalidException, AuthTokenExpiredException, Exception):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired code.",
        )

    # Register email as verified asset — scanning is only permitted after this
    await asset_service.register_verified_email(
        user_id=user.id,
        email=str(body.email),
    )

    return TokenResponse(access_token=token)
```

---

## 2.14 Router and Rate Limiting

**Implementation note:** The `limiter` instance lives in `backend/app/core/rate_limit.py`, NOT in `main.py`. Importing from `main.py` creates a circular import (`main → router → auth → main`). Create a dedicated module instead:

```python
# backend/app/core/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter instance — import from here in all endpoint modules.
limiter = Limiter(key_func=get_remote_address)
```

In `backend/app/main.py`, import from `core.rate_limit`:

```python
# CHANGE IN: backend/app/main.py
# Replace any inline Limiter() instantiation with:
from backend.app.core.rate_limit import limiter
```

Add the rate limit decorators to the auth endpoints in `auth.py`:

```python
# ADDITION TO: backend/app/api/v1/auth.py
# Add these imports at the top:
from backend.app.core.rate_limit import limiter

# Add these decorators to the endpoint functions:
# @router.post("/otp/request", ...) becomes:
# @router.post("/otp/request", status_code=202)
# @limiter.limit("3/15minutes")
# async def request_otp(request: Request, ...):

# @router.post("/otp/verify", ...) becomes:
# @router.post("/otp/verify", response_model=TokenResponse)
# @limiter.limit("10/15minutes")
# async def verify_otp(request: Request, ...):
# NOTE: request: Request parameter must be present for slowapi to work
```

---

## 2.15 API Router

Create `backend/app/api/router.py` using the exact implementation in **CLAUDE-CODE-BRIEFING.md** under "api/router.py — Complete Implementation".

---

## 2.16 Run Migrations

```bash
# From repo root
uv run alembic revision --autogenerate -m "auth_and_assets"
uv run alembic upgrade head
uv run alembic current  # Must show: (head)
```

---

## 2.17 Tests

### tests/unit/auth/test_service.py

```python
# tests/unit/auth/test_service.py
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.auth.service import AuthService, _generate_code, _hash_code
from backend.app.core.exceptions import AuthTokenInvalidException


def test_generate_code_is_six_digits() -> None:
    code = _generate_code()
    assert len(code) == 6
    assert code.isdigit()
    assert 100000 <= int(code) <= 999999


def test_generate_code_produces_different_values() -> None:
    codes = {_generate_code() for _ in range(100)}
    # With 900,000 possible values, getting 100 unique values from 100 calls
    # should be essentially guaranteed
    assert len(codes) > 90


def test_hash_code_is_deterministic() -> None:
    assert _hash_code("123456") == _hash_code("123456")


def test_hash_code_different_inputs_different_hashes() -> None:
    assert _hash_code("123456") != _hash_code("654321")


@pytest.mark.asyncio
async def test_request_otp_returns_none_when_rate_limited() -> None:
    token_repo = AsyncMock()
    token_repo.count_active_for_email.return_value = 3  # At limit
    user_repo = AsyncMock()
    session = AsyncMock()

    service = AuthService(session=session, user_repo=user_repo, token_repo=token_repo)
    result = await service.request_otp(email="test@example.com", requesting_ip="1.2.3.4")

    assert result is None
    token_repo.count_active_for_email.assert_called_once_with("test@example.com")


@pytest.mark.asyncio
async def test_request_otp_creates_user_on_first_signin() -> None:
    token_repo = AsyncMock()
    token_repo.count_active_for_email.return_value = 0
    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = None  # No existing user
    session = AsyncMock()
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    service = AuthService(session=session, user_repo=user_repo, token_repo=token_repo)
    result = await service.request_otp(
        email="new@example.com",
        requesting_ip="1.2.3.4",
        privacy_policy_accepted=True,
    )

    assert result is not None
    assert len(result) == 6
    session.add.assert_called()  # User and token both added


@pytest.mark.asyncio
async def test_verify_otp_raises_invalid_for_wrong_code() -> None:
    token_repo = AsyncMock()
    token_repo.get_valid_token.return_value = None  # No matching token

    user_repo = AsyncMock()
    session = AsyncMock()

    service = AuthService(session=session, user_repo=user_repo, token_repo=token_repo)

    with pytest.raises(AuthTokenInvalidException):
        await service.verify_otp(email="test@example.com", code="000000")


@pytest.mark.asyncio
async def test_verify_otp_raises_same_exception_for_all_failure_modes() -> None:
    """All failure modes must raise AuthTokenInvalidException — same type, same message."""
    token_repo = AsyncMock()
    user_repo = AsyncMock()
    session = AsyncMock()
    service = AuthService(session=session, user_repo=user_repo, token_repo=token_repo)

    # Wrong code
    token_repo.get_valid_token.return_value = None
    with pytest.raises(AuthTokenInvalidException) as exc_info_1:
        await service.verify_otp(email="test@example.com", code="000000")

    # Valid token but deleted user
    from backend.app.auth.models import AuthToken
    from datetime import datetime, timezone, timedelta
    valid_token = AuthToken(
        email="test@example.com",
        code_hash=_hash_code("123456"),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    token_repo.get_valid_token.return_value = valid_token
    session.flush = AsyncMock()

    from backend.app.auth.models import User
    deleted_user = User(deleted_at=datetime.now(timezone.utc))
    user_repo.get_by_email.return_value = deleted_user

    with pytest.raises(AuthTokenInvalidException) as exc_info_2:
        await service.verify_otp(email="test@example.com", code="123456")

    # Both raise the same message
    assert str(exc_info_1.value.message) == str(exc_info_2.value.message)
```

### tests/api/test_auth_endpoints.py

```python
# tests/api/test_auth_endpoints.py
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_request_otp_always_returns_202(client: AsyncClient) -> None:
    """Returns 202 regardless of whether email exists or rate limit applies."""
    response = await client.post(
        "/api/v1/auth/otp/request",
        json={"email": "any@example.com", "privacy_policy_accepted": True},
    )
    assert response.status_code == 202
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_request_otp_rejects_invalid_email(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/otp/request",
        json={"email": "not-an-email"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_verify_otp_rejects_non_numeric_code(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/otp/verify",
        json={"email": "test@example.com", "code": "abcdef"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_verify_otp_rejects_wrong_length_code(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/otp/verify",
        json={"email": "test@example.com", "code": "12345"},  # 5 digits, not 6
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_verify_otp_returns_401_for_wrong_code(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/otp/verify",
        json={"email": "test@example.com", "code": "000000"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired code."


@pytest.mark.asyncio
async def test_authenticated_endpoint_rejects_missing_token(client: AsyncClient) -> None:
    """Verifies the auth dependency works on a protected endpoint."""
    # Use /account/audit-log — it's a real auth-protected endpoint (scans/ is a stub until Stage 6)
    response = await client.get("/api/v1/account/audit-log")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_authenticated_endpoint_rejects_invalid_token(client: AsyncClient) -> None:
    response = await client.get(
        "/api/v1/account/audit-log",
        headers={"Authorization": "Bearer invalidtoken"},
    )
    assert response.status_code == 401
```

---

## Stage 2 Verification

```bash
uv run alembic current  # Must show: (head)
uv run pytest tests/unit/auth/ -v
uv run pytest tests/api/test_auth_endpoints.py -v
uv run python scripts/check_imports.py
```

All must pass before proceeding to Stage 3.
