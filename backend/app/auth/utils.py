# backend/app/auth/utils.py
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

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
    Never raises JWTError — always converts to ValueError.
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
    except JWTError as exc:
        raise ValueError(f"Invalid token: {exc}") from exc
