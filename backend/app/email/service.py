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
        self._configured = settings.resend_api_key is not None and bool(
            settings.resend_api_key.get_secret_value()
        )
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

        import resend

        from backend.app.email.templates.otp import otp_html, otp_text

        try:
            resend.Emails.send(
                {
                    "from": (
                        f"{settings.email_from_name}"
                        f" <{settings.email_from_address}>"
                    ),
                    "to": [to_email],
                    "subject": "Your Zima sign-in code",
                    "html": otp_html(code),
                    "text": otp_text(code),
                }
            )
            logger.info("email.otp_sent")
        except Exception as exc:
            # Log but do not raise — token is already stored, user can request another
            logger.error("email.send_failed", error=str(exc))
