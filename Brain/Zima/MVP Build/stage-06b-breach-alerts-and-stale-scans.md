← [[MVP Master|Stage Progress]]

# Stage 6b — Breach Alert Email Template and Stale Scan Startup Check

**This stage supplements Stage 6. Implement it as part of Stage 6, not after.**

The notification logic in `orchestrator.py` references `_email_service.send_breach_alert()` and the breach alert templates. Those are defined here.

---

## Files to Create in This Stage

1. `backend/app/email/templates/breach_alert.py`
2. Add `send_breach_alert` to `backend/app/email/service.py`
3. Add startup stale scan check to `backend/app/main.py`

---

## 6b.1 Breach Alert Template

```python
# backend/app/email/templates/breach_alert.py


def breach_alert_html(
    monitored_email: str,
    breach_title: str,
    breach_date: str,
    data_classes: list[str],
    dashboard_url: str = "https://yourdomain.com/dashboard",
) -> str:
    data_items = "".join(f"<li style='margin-bottom:4px'>{d}</li>" for d in data_classes)
    return f"""<!DOCTYPE html>
<html>
<body style="font-family: sans-serif; max-width: 560px; margin: 0 auto; padding: 24px; color: #0f172a;">
  <h2 style="margin-bottom: 8px;">New breach detected</h2>
  <p style="color: #475569; margin-bottom: 24px;">
    A monitored email address was found in a data breach.
  </p>
  <table style="width: 100%; border-collapse: collapse; margin-bottom: 24px;">
    <tr>
      <td style="padding: 10px 12px; font-weight: 600; background: #f8fafc; width: 35%; border: 1px solid #e2e8f0;">Email</td>
      <td style="padding: 10px 12px; border: 1px solid #e2e8f0;">{monitored_email}</td>
    </tr>
    <tr>
      <td style="padding: 10px 12px; font-weight: 600; background: #f8fafc; border: 1px solid #e2e8f0;">Breach</td>
      <td style="padding: 10px 12px; border: 1px solid #e2e8f0;">{breach_title}</td>
    </tr>
    <tr>
      <td style="padding: 10px 12px; font-weight: 600; background: #f8fafc; border: 1px solid #e2e8f0;">Date</td>
      <td style="padding: 10px 12px; border: 1px solid #e2e8f0;">{breach_date}</td>
    </tr>
    <tr>
      <td style="padding: 10px 12px; font-weight: 600; background: #f8fafc; border: 1px solid #e2e8f0; vertical-align: top;">Data exposed</td>
      <td style="padding: 10px 12px; border: 1px solid #e2e8f0;">
        <ul style="margin: 0; padding-left: 18px;">{data_items}</ul>
      </td>
    </tr>
  </table>
  <a href="{dashboard_url}"
     style="display: inline-block; background: #0f172a; color: #ffffff;
            padding: 12px 24px; border-radius: 6px; text-decoration: none;
            font-weight: 600; margin-bottom: 32px;">
    View your dashboard →
  </a>
  <p style="color: #94a3b8; font-size: 13px; border-top: 1px solid #e2e8f0; padding-top: 16px;">
    You're receiving this because you monitor this email address with Zima.
  </p>
</body>
</html>"""


def breach_alert_text(
    monitored_email: str,
    breach_title: str,
    breach_date: str,
    data_classes: list[str],
    dashboard_url: str = "https://yourdomain.com/dashboard",
) -> str:
    data_list = ", ".join(data_classes) if data_classes else "unknown"
    return (
        f"New breach detected\n"
        f"{'=' * 40}\n\n"
        f"Email:        {monitored_email}\n"
        f"Breach:       {breach_title}\n"
        f"Date:         {breach_date}\n"
        f"Data exposed: {data_list}\n\n"
        f"View your dashboard: {dashboard_url}\n\n"
        f"You're receiving this because you monitor this email address with Zima."
    )
```

---

## 6b.2 EmailService — send_breach_alert Addition

Add this method to the `EmailService` class in `backend/app/email/service.py`:

```python
# ADDITION TO: backend/app/email/service.py
# Add this method to the EmailService class, after send_otp:

    async def send_breach_alert(
        self,
        to_email: str,
        monitored_email: str,
        breach_title: str,
        breach_date: str,
        data_classes: list[str],
    ) -> None:
        """
        Sends a breach alert notification.
        to_email: recipient address (the user's primary sign-in email)
        monitored_email: the email address that was found in the breach
        Never raises — failures are logged and silently swallowed.
        """
        if not self._configured:
            logger.info(
                "email.breach_alert_dev_console",
                to=to_email,
                breach=breach_title,
            )
            return

        from backend.app.email.templates.breach_alert import (
            breach_alert_html,
            breach_alert_text,
        )
        import resend

        try:
            resend.Emails.send({
                "from": f"{settings.email_from_name} <{settings.email_from_address}>",
                "to": [to_email],
                "subject": f"Breach detected: {breach_title}",
                "html": breach_alert_html(
                    monitored_email, breach_title, breach_date, data_classes
                ),
                "text": breach_alert_text(
                    monitored_email, breach_title, breach_date, data_classes
                ),
            })
            logger.info("email.breach_alert_sent", breach=breach_title)
        except Exception as exc:
            logger.error("email.breach_alert_failed", error=str(exc))
```

---

## 6b.3 Startup Stale Scan Check

Add this to the `lifespan` function in `backend/app/main.py`. This clears any scans left in RUNNING state from a previous crashed application instance.

```python
# ADDITION TO: backend/app/main.py
# Update the lifespan function to include the stale scan check:

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    check_environment()

    # Clear stale scans from any previous crashed instance
    from backend.app.db.session import AsyncSessionLocal
    from backend.app.db.repositories.scans import ScanRepository
    async with AsyncSessionLocal() as session:
        scan_repo = ScanRepository(session)
        stale_count = await scan_repo.mark_stale_scans_failed()
        await session.commit()
        if stale_count > 0:
            from backend.app.core.logging import get_logger
            get_logger(__name__).info(
                "startup.stale_scans_cleared", count=stale_count
            )

    yield
```

---

## 6b.4 Tests

### tests/unit/test_email_templates.py

```python
# tests/unit/test_email_templates.py
from backend.app.email.templates.breach_alert import breach_alert_html, breach_alert_text
from backend.app.email.templates.otp import otp_html, otp_text


def test_breach_alert_html_contains_required_fields() -> None:
    html = breach_alert_html(
        monitored_email="victim@example.com",
        breach_title="Adobe",
        breach_date="2013-10-04",
        data_classes=["Passwords", "Email addresses"],
    )
    assert "victim@example.com" in html
    assert "Adobe" in html
    assert "2013-10-04" in html
    assert "Passwords" in html
    assert "Email addresses" in html


def test_breach_alert_text_contains_required_fields() -> None:
    text = breach_alert_text(
        monitored_email="victim@example.com",
        breach_title="LinkedIn",
        breach_date="2012-05-05",
        data_classes=["Passwords"],
    )
    assert "victim@example.com" in text
    assert "LinkedIn" in text
    assert "2012-05-05" in text
    assert "Passwords" in text


def test_breach_alert_html_handles_empty_data_classes() -> None:
    html = breach_alert_html(
        monitored_email="test@example.com",
        breach_title="Unknown",
        breach_date="2024-01-01",
        data_classes=[],
    )
    assert "test@example.com" in html


def test_otp_html_contains_code() -> None:
    html = otp_html("123456")
    assert "123456" in html


def test_otp_text_contains_code() -> None:
    text = otp_text("123456")
    assert "123456" in text
```

### tests/unit/auth/test_email_service.py

```python
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
        MagicMock(resend_api_key=None),
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
        MagicMock(resend_api_key=None),
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
    import resend

    monkeypatch.setattr(
        "backend.app.email.service.settings",
        MagicMock(
            resend_api_key=MagicMock(get_secret_value=lambda: "test-key"),
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
```

### Stale Scan Tests

```python
# tests/unit/test_stale_scans.py
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.enums import ScanStatus, Tier
from backend.app.db.repositories.scans import ScanRepository
from backend.app.jobs.models import Scan
from tests.factories import UserFactory


@pytest.mark.asyncio
async def test_mark_stale_scans_updates_old_running_scans(
    db_session: AsyncSession,
) -> None:
    user = UserFactory.build()
    db_session.add(user)
    await db_session.flush()

    stale_scan = Scan(
        user_id=user.id,
        tier="core",
        status=ScanStatus.RUNNING.value,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=15),
    )
    db_session.add(stale_scan)
    await db_session.commit()

    scan_repo = ScanRepository(db_session)
    count = await scan_repo.mark_stale_scans_failed(stale_after_minutes=10)
    await db_session.commit()

    assert count == 1
    await db_session.refresh(stale_scan)
    assert stale_scan.status == ScanStatus.FAILED.value
    assert stale_scan.completed_at is not None


@pytest.mark.asyncio
async def test_mark_stale_scans_ignores_recent_running_scans(
    db_session: AsyncSession,
) -> None:
    user = UserFactory.build()
    db_session.add(user)
    await db_session.flush()

    recent_scan = Scan(
        user_id=user.id,
        tier="core",
        status=ScanStatus.RUNNING.value,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=2),
    )
    db_session.add(recent_scan)
    await db_session.commit()

    scan_repo = ScanRepository(db_session)
    count = await scan_repo.mark_stale_scans_failed(stale_after_minutes=10)
    await db_session.commit()

    assert count == 0
    await db_session.refresh(recent_scan)
    assert recent_scan.status == ScanStatus.RUNNING.value


@pytest.mark.asyncio
async def test_mark_stale_scans_ignores_completed_scans(
    db_session: AsyncSession,
) -> None:
    user = UserFactory.build()
    db_session.add(user)
    await db_session.flush()

    completed_scan = Scan(
        user_id=user.id,
        tier="core",
        status=ScanStatus.COMPLETED.value,
        started_at=datetime.now(timezone.utc) - timedelta(hours=2),
        completed_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )
    db_session.add(completed_scan)
    await db_session.commit()

    scan_repo = ScanRepository(db_session)
    count = await scan_repo.mark_stale_scans_failed(stale_after_minutes=10)

    assert count == 0
```

---

## Stage 6b Verification

```bash
uv run pytest tests/unit/test_email_templates.py -v
uv run pytest tests/unit/auth/test_email_service.py -v
uv run pytest tests/unit/test_stale_scans.py -v
uv run python scripts/check_imports.py
```
