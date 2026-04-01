# tests/unit/auth/test_email_service.py
from unittest.mock import MagicMock, patch

import pytest

from backend.app.email.service import EmailService


@pytest.mark.asyncio
async def test_send_otp_logs_to_console_when_no_api_key(
    monkeypatch,
) -> None:
    """In dev (no API key), OTP is logged — no Resend call."""
    monkeypatch.setattr(
        "backend.app.email.service.settings",
        MagicMock(resend_api_key=None, is_production=False),
    )
    service = EmailService()
    # Should not raise, and should not call resend
    await service.send_otp("test@example.com", "123456")


@pytest.mark.asyncio
async def test_send_breach_alert_logs_to_console_when_no_api_key(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "backend.app.email.service.settings",
        MagicMock(resend_api_key=None, is_production=False),
    )
    service = EmailService()
    await service.send_breach_alert(
        to_email="user@example.com",
        monitored_email="victim@example.com",
        breach_title="Adobe",
        breach_date="2013-10-04",
        data_classes=["Passwords"],
    )
    # No exception means pass


@pytest.mark.asyncio
async def test_send_breach_alert_does_not_raise_on_resend_error(
    monkeypatch,
) -> None:
    """EmailService must never raise — failures are swallowed."""
    monkeypatch.setattr(
        "backend.app.email.service.settings",
        MagicMock(
            resend_api_key=MagicMock(get_secret_value=lambda: "test-key"),
            is_production=False,
            email_from_name="Zima",
            email_from_address="noreply@test.com",
        ),
    )

    with patch("resend.Emails.send", side_effect=Exception("Resend unavailable")):
        service = EmailService()
        # Must not raise
        await service.send_breach_alert(
            to_email="user@example.com",
            monitored_email="victim@example.com",
            breach_title="Adobe",
            breach_date="2013-10-04",
            data_classes=["Passwords"],
        )
