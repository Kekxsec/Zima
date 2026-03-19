# tests/unit/auth/test_service.py
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from backend.app.auth.models import AuthToken, User
from backend.app.auth.service import (
    OTP_LOCKOUT_MINUTES,
    OTP_MAX_FAILURES,
    AuthService,
    _generate_code,
    _hash_code,
)
from backend.app.core.exceptions import AuthTokenInvalidException


def _make_service(
    *,
    token_repo: AsyncMock | None = None,
    user_repo: AsyncMock | None = None,
    session: AsyncMock | None = None,
) -> AuthService:
    """Helper: builds AuthService with mocked dependencies."""
    if user_repo is None:
        user_repo = AsyncMock()
        # Default: no user found — tests that need a user set this explicitly.
        # This prevents MagicMock attribute access from triggering the lockout
        # check with an unpredictable truthy value.
        user_repo.get_by_email.return_value = None
    return AuthService(
        session=session or AsyncMock(),
        user_repo=user_repo or AsyncMock(),
        token_repo=token_repo or AsyncMock(),
        audit_repo=AsyncMock(),
    )


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

    service = _make_service(token_repo=token_repo)
    result = await service.request_otp(
        email="test@example.com", requesting_ip="1.2.3.4"
    )

    assert result is None
    token_repo.count_active_for_email.assert_called_once_with("test@example.com")


@pytest.mark.asyncio
async def test_request_otp_creates_user_on_first_signin() -> None:
    token_repo = AsyncMock()
    token_repo.count_active_for_email.return_value = 0
    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = None  # No existing user
    session = AsyncMock()
    session.add = MagicMock()  # add() is synchronous
    session.flush = AsyncMock()
    session.commit = AsyncMock()

    service = _make_service(token_repo=token_repo, user_repo=user_repo, session=session)
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

    service = _make_service(token_repo=token_repo)

    with pytest.raises(AuthTokenInvalidException):
        await service.verify_otp(email="test@example.com", code="000000")


@pytest.mark.asyncio
async def test_verify_otp_raises_same_exception_for_all_failure_modes() -> None:
    """All failure modes must raise AuthTokenInvalidException — same type, same message."""
    token_repo = AsyncMock()
    user_repo = AsyncMock()
    session = AsyncMock()
    service = _make_service(token_repo=token_repo, user_repo=user_repo, session=session)

    # Wrong code — user_repo returns None (no user)
    user_repo.get_by_email.return_value = None
    token_repo.get_valid_token.return_value = None
    with pytest.raises(AuthTokenInvalidException) as exc_info_1:
        await service.verify_otp(email="test@example.com", code="000000")

    # Valid token but deleted user
    valid_token = AuthToken(
        email="test@example.com",
        code_hash=_hash_code("123456"),
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    token_repo.get_valid_token.return_value = valid_token
    session.commit = AsyncMock()

    deleted_user = User(deleted_at=datetime.now(UTC))
    user_repo.get_by_email.return_value = deleted_user

    with pytest.raises(AuthTokenInvalidException) as exc_info_2:
        await service.verify_otp(email="test@example.com", code="123456")

    # Both raise the same message
    assert str(exc_info_1.value.message) == str(exc_info_2.value.message)


@pytest.mark.asyncio
async def test_verify_otp_increments_fail_count_on_bad_code() -> None:
    """Each failed verification increments otp_fail_count on the user."""
    token_repo = AsyncMock()
    token_repo.get_valid_token.return_value = None

    user = User()
    user.otp_fail_count = 0
    user.otp_locked_until = None

    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = user

    service = _make_service(token_repo=token_repo, user_repo=user_repo)

    with pytest.raises(AuthTokenInvalidException):
        await service.verify_otp(email="test@example.com", code="000000")

    assert user.otp_fail_count == 1
    assert user.otp_locked_until is None


@pytest.mark.asyncio
async def test_verify_otp_locks_account_after_max_failures() -> None:
    """Account is locked after OTP_MAX_FAILURES consecutive failures."""
    token_repo = AsyncMock()
    token_repo.get_valid_token.return_value = None

    user = User()
    user.otp_fail_count = OTP_MAX_FAILURES - 1  # One away from lockout
    user.otp_locked_until = None

    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = user

    service = _make_service(token_repo=token_repo, user_repo=user_repo)

    with pytest.raises(AuthTokenInvalidException):
        await service.verify_otp(email="test@example.com", code="000000")

    assert user.otp_fail_count == OTP_MAX_FAILURES
    assert user.otp_locked_until is not None
    # Lockout window should be approximately OTP_LOCKOUT_MINUTES from now
    expected_unlock = datetime.now(UTC) + timedelta(minutes=OTP_LOCKOUT_MINUTES)
    assert abs((user.otp_locked_until - expected_unlock).total_seconds()) < 5


@pytest.mark.asyncio
async def test_verify_otp_blocks_locked_account() -> None:
    """A locked account is rejected even when a valid token exists."""
    token_repo = AsyncMock()
    # Even if the token would be valid, lockout fires before the token check
    token_repo.get_valid_token.return_value = AuthToken(
        email="test@example.com",
        code_hash=_hash_code("123456"),
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )

    user = User()
    user.otp_fail_count = OTP_MAX_FAILURES
    user.otp_locked_until = datetime.now(UTC) + timedelta(minutes=10)

    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = user

    service = _make_service(token_repo=token_repo, user_repo=user_repo)

    with pytest.raises(AuthTokenInvalidException):
        await service.verify_otp(email="test@example.com", code="123456")

    # Token should NOT have been consumed — lockout fired before token check
    token_repo.get_valid_token.assert_not_called()


@pytest.mark.asyncio
async def test_verify_otp_resets_fail_count_on_success() -> None:
    """Successful verification resets the failure counter and clears the lockout."""
    valid_token = AuthToken(
        email="test@example.com",
        code_hash=_hash_code("123456"),
        expires_at=datetime.now(UTC) + timedelta(minutes=10),
    )
    token_repo = AsyncMock()
    token_repo.get_valid_token.return_value = valid_token

    user = User()
    user.otp_fail_count = 3
    user.otp_locked_until = None

    user_repo = AsyncMock()
    user_repo.get_by_email.return_value = user

    session = AsyncMock()
    service = _make_service(token_repo=token_repo, user_repo=user_repo, session=session)

    result_user, jwt_token = await service.verify_otp(
        email="test@example.com", code="123456"
    )

    assert result_user.otp_fail_count == 0
    assert result_user.otp_locked_until is None
    assert jwt_token != ""
