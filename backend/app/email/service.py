# backend/app/email/service.py
import asyncio

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
        self._configured = settings.resend_api_key is not None and bool(
            settings.resend_api_key.get_secret_value()
        )

        if settings.is_production and not self._configured:
            # Hard fail at startup rather than silently logging OTP codes to stdout
            raise RuntimeError(
                "RESEND_API_KEY must be set in production. "
                "Email is not optional when APP_ENV=production."
            )

        if self._configured:
            import resend

            resend.api_key = settings.resend_api_key.get_secret_value()  # type: ignore[union-attr]

    async def send_otp(self, to_email: str, code: str) -> None:
        """Sends a sign-in OTP code to the given email address."""
        if not self._configured:
            # Development only — log that a code was issued but never log the raw code.
            # The code is visible in the DB (as a hash) and must be retrieved via
            # the auth token repository for testing. Never log raw OTP codes.
            logger.info("email.otp_dev_console", email=to_email)
            return

        import resend

        from backend.app.email.templates.otp import otp_html, otp_text

        params = {
            "from": (f"{settings.email_from_name} <{settings.email_from_address}>"),
            "to": [to_email],
            "subject": "Your Zima sign-in code",
            "html": otp_html(code),
            "text": otp_text(code),
        }

        try:
            # resend.Emails.send() is synchronous — run in a thread to avoid
            # blocking the event loop during the outbound HTTP request.
            await asyncio.to_thread(resend.Emails.send, params)  # type: ignore[arg-type]
            logger.info("email.otp_sent")
        except Exception as exc:
            # Log but do not raise — token is already stored, user can request another
            logger.error("email.send_failed", error=str(exc))

    async def send_breach_alert(
        self,
        to_email: str,
        monitored_email: str,
        breach_title: str,
        breach_date: str,
        data_classes: list[str],
    ) -> None:
        """Sends a breach alert notification email. Never raises."""
        if not self._configured:
            logger.info(
                "email.breach_alert_dev_console",
                to_email=to_email,
                breach_title=breach_title,
            )
            return

        import resend

        from backend.app.email.templates.breach_alert import (
            breach_alert_html,
            breach_alert_text,
        )

        params = {
            "from": f"{settings.email_from_name} <{settings.email_from_address}>",
            "to": [to_email],
            "subject": f"Breach detected: {breach_title}",
            "html": breach_alert_html(
                monitored_email, breach_title, breach_date, data_classes
            ),
            "text": breach_alert_text(
                monitored_email, breach_title, breach_date, data_classes
            ),
        }
        try:
            await asyncio.to_thread(resend.Emails.send, params)  # type: ignore[arg-type]
            logger.info("email.breach_alert_sent", breach=breach_title)
        except Exception as exc:
            logger.error("email.breach_alert_failed", error=str(exc))
