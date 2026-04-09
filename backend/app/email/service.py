# backend/app/email/service.py
import asyncio

from backend.app.core.config import settings
from backend.app.core.logging import get_logger

logger = get_logger(__name__)

_MAX_SEND_ATTEMPTS: int = 3


async def _send_with_retry(
    send_fn: object,
    params: dict,
    log_tag: str,
    *,
    max_attempts: int = _MAX_SEND_ATTEMPTS,
) -> None:
    """
    Calls ``resend.Emails.send(params)`` in a thread pool, retrying up to
    ``max_attempts`` times with exponential back-off (1s, 2s, 4s…).
    Logs WARN on each transient failure and ERROR only when all retries are
    exhausted — then swallows the exception so callers never raise.
    """
    import resend  # noqa: PLC0415 — import only when configured

    for attempt in range(1, max_attempts + 1):
        try:
            await asyncio.to_thread(resend.Emails.send, params)  # type: ignore[arg-type]
            return
        except Exception as exc:
            if attempt < max_attempts:
                wait = 2 ** (attempt - 1)
                logger.warning(
                    "email.send_retry",
                    tag=log_tag,
                    attempt=attempt,
                    wait_seconds=wait,
                    error=str(exc),
                )
                await asyncio.sleep(wait)
            else:
                logger.error(
                    "email.send_failed_permanently",
                    tag=log_tag,
                    attempts=max_attempts,
                    error=str(exc),
                )


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

        await _send_with_retry(resend.Emails.send, params, "otp_send")
        logger.info("email.otp_sent")

    async def send_domain_otp(self, domain: str, code: str) -> None:
        """Sends a domain verification OTP to admin@<domain>. Never raises."""
        to_email = f"admin@{domain}"
        if not self._configured:
            logger.info("email.domain_otp_dev_console", to_email=to_email)
            return

        import resend

        params = {
            "from": f"{settings.email_from_name} <{settings.email_from_address}>",
            "to": [to_email],
            "subject": f"Verify your domain on Zima: {domain}",
            "text": (
                f"Your Zima domain verification code for {domain} is: {code}\n\n"
                "This code expires in 15 minutes. "
                "If you did not request this, please ignore this email."
            ),
            "html": (
                f"<p>Your Zima domain verification code for"
                f" <strong>{domain}</strong> is:</p>"
                f"<p style='font-size:24px;font-weight:bold;letter-spacing:4px'>"
                f"{code}</p>"
                "<p>This code expires in 15 minutes. "
                "If you did not request this, please ignore this email.</p>"
            ),
        }
        await _send_with_retry(resend.Emails.send, params, "domain_otp_send")
        logger.info("email.domain_otp_sent", domain=domain)

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
        await _send_with_retry(resend.Emails.send, params, "breach_alert_send")
        logger.info("email.breach_alert_sent", breach=breach_title)
