# backend/app/auth/utils.py
import uuid
from datetime import UTC, datetime, timedelta

import jwt

from backend.app.core.config import settings


def create_access_token(subject: str, tier: str) -> str:
    """
    Creates a signed JWT access token.
    subject: str representation of user UUID
    tier: user's current tier name (e.g. "core", "plus")

    Each token receives a unique `jti` (JWT ID) so individual tokens can be
    revoked via the TokenBlacklist without invalidating all sessions.
    """
    expire = datetime.now(UTC) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    issued_at = datetime.now(UTC)
    payload = {
        "sub": subject,
        "tier": tier,
        "exp": expire,
        "iat": issued_at,
        "jti": str(uuid.uuid4()),
        "type": "access",
    }
    return str(
        jwt.encode(
            payload,
            settings.jwt_secret_key.get_secret_value(),
            algorithm=settings.jwt_algorithm,
        )
    )


def _coerce_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    if isinstance(value, int | float):
        return datetime.fromtimestamp(float(value), tz=UTC)
    return None


def create_companion_token(
    user_id: str, session_id: str, jti: str, expire_days: int = 7
) -> str:
    """
    Creates a signed JWT companion token for the Rust binary.
    Uses Bearer header only — never a cookie.
    jti must be the same value stored in CompanionSession.companion_jti so that
    re-registration immediately invalidates any prior token.
    """
    expire = datetime.now(UTC) + timedelta(days=expire_days)
    issued_at = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "session_id": session_id,
        "type": "companion",
        "exp": expire,
        "iat": issued_at,
        "jti": jti,
    }
    return str(
        jwt.encode(
            payload,
            settings.jwt_secret_key.get_secret_value(),
            algorithm=settings.jwt_algorithm,
        )
    )


def decode_companion_token(token: str) -> dict[str, object]:
    """
    Decodes and validates a companion JWT.
    Raises ValueError if invalid, expired, or wrong type.
    """
    try:
        payload: dict[str, object] = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "companion":
            raise ValueError("Token type is not 'companion'")
        issued_at = _coerce_timestamp(payload.get("iat"))
        if issued_at is not None:
            payload["iat"] = issued_at
        expires_at = _coerce_timestamp(payload.get("exp"))
        if expires_at is not None:
            payload["exp"] = expires_at
        return payload
    except jwt.PyJWTError as exc:
        raise ValueError(f"Invalid companion token: {exc}") from exc


def create_extension_token(
    user_id: str, session_id: str, jti: str, expire_minutes: int | None = None
) -> str:
    """
    Creates a signed JWT extension token for the browser extension.
    Uses Bearer header only — same pattern as companion tokens.
    jti must match ExtensionSession.extension_jti for per-session revocation.
    """
    ttl_minutes = (
        expire_minutes
        if expire_minutes is not None
        else settings.extension_token_expire_minutes
    )
    expire = datetime.now(UTC) + timedelta(minutes=ttl_minutes)
    issued_at = datetime.now(UTC)
    payload = {
        "sub": user_id,
        "session_id": session_id,
        "type": "extension",
        "exp": expire,
        "iat": issued_at,
        "jti": jti,
    }
    return str(
        jwt.encode(
            payload,
            settings.jwt_secret_key.get_secret_value(),
            algorithm=settings.jwt_algorithm,
        )
    )


def decode_extension_token(token: str) -> dict[str, object]:
    """
    Decodes and validates an extension JWT.
    Raises ValueError if invalid, expired, or wrong type.
    """
    try:
        payload: dict[str, object] = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "extension":
            raise ValueError("Token type is not 'extension'")
        issued_at = _coerce_timestamp(payload.get("iat"))
        if issued_at is not None:
            payload["iat"] = issued_at
        expires_at = _coerce_timestamp(payload.get("exp"))
        if expires_at is not None:
            payload["exp"] = expires_at
        return payload
    except jwt.PyJWTError as exc:
        raise ValueError(f"Invalid extension token: {exc}") from exc


def decode_access_token(token: str) -> dict[str, object]:
    """
    Decodes and validates a JWT access token.
    Raises ValueError if the token is invalid, expired, or wrong type.
    Never raises jwt.PyJWTError — always converts to ValueError.

    Both `iat` and `exp` are coerced to timezone-aware datetimes so callers
    can compute remaining TTL without re-parsing Unix timestamps.
    """
    try:
        payload: dict[str, object] = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "access":
            raise ValueError("Token type is not 'access'")
        issued_at = _coerce_timestamp(payload.get("iat"))
        if issued_at is not None:
            payload["iat"] = issued_at
        expires_at = _coerce_timestamp(payload.get("exp"))
        if expires_at is not None:
            payload["exp"] = expires_at
        return payload
    except jwt.PyJWTError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc
