# tests/unit/test_email_templates.py
from backend.app.email.templates.breach_alert import (
    breach_alert_html,
    breach_alert_text,
)
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
