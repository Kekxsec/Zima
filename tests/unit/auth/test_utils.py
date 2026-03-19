# tests/unit/auth/test_utils.py
from datetime import UTC

import pytest

from backend.app.auth.utils import create_access_token, decode_access_token


def test_create_and_decode_roundtrip() -> None:
    token = create_access_token(subject="some-uuid", tier="core")
    payload = decode_access_token(token)
    assert payload["sub"] == "some-uuid"
    assert payload["tier"] == "core"
    assert payload["type"] == "access"


def test_decode_rejects_tampered_token() -> None:
    token = create_access_token(subject="some-uuid", tier="core")
    tampered = token[:-4] + "xxxx"
    with pytest.raises(ValueError):
        decode_access_token(tampered)


def test_decode_rejects_wrong_type() -> None:
    """A token with type != 'access' must be rejected."""
    from datetime import datetime, timedelta

    import jwt

    from backend.app.core.config import settings

    payload = {
        "sub": "some-uuid",
        "tier": "core",
        "exp": datetime.now(UTC) + timedelta(minutes=60),
        "type": "refresh",  # Wrong type
    }
    bad_token = jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )
    with pytest.raises(ValueError, match="Token type is not 'access'"):
        decode_access_token(bad_token)


def test_decode_rejects_garbage_string() -> None:
    with pytest.raises(ValueError):
        decode_access_token("notavalidtoken")
