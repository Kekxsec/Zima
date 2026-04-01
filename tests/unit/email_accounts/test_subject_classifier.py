# tests/unit/email_accounts/test_subject_classifier.py
"""Unit tests for subject-line classification in AccountDiscoveryService."""

import pytest

from backend.app.db.models.email_accounts import DiscoveredAccountSourceType
from backend.app.email_accounts.service import _classify_subject


class TestClassifySubject:
    def test_none_returns_other(self) -> None:
        assert _classify_subject(None) == DiscoveredAccountSourceType.OTHER

    def test_empty_returns_other(self) -> None:
        assert _classify_subject("") == DiscoveredAccountSourceType.OTHER

    # --- Account confirmation ---
    @pytest.mark.parametrize(
        "subject",
        [
            "Welcome to GitHub! Please verify your email address",
            "Confirm your Spotify account",
            "Activate your new account",
            "Thanks for signing up for Notion",
            "Thanks for joining Netflix",
            "Complete your registration",
            "Validate your email address",
        ],
    )
    def test_account_confirmation(self, subject: str) -> None:
        assert (
            _classify_subject(subject)
            == DiscoveredAccountSourceType.ACCOUNT_CONFIRMATION
        )

    # --- Password reset ---
    @pytest.mark.parametrize(
        "subject",
        [
            "Reset your Spotify password",
            "Forgot your GitHub password?",
            "Recover your PayPal password",
            "Change your password",
        ],
    )
    def test_password_reset(self, subject: str) -> None:
        assert _classify_subject(subject) == DiscoveredAccountSourceType.PASSWORD_RESET

    # --- Receipt ---
    @pytest.mark.parametrize(
        "subject",
        [
            "Your receipt from Stripe — $19.99",
            "Order confirmation #112-3456789",
            "Invoice #INV-001 from Acme",
            "Your purchase is confirmed",
            "Payment confirmation — thank you",
        ],
    )
    def test_receipt(self, subject: str) -> None:
        assert _classify_subject(subject) == DiscoveredAccountSourceType.RECEIPT

    # --- Security alert ---
    @pytest.mark.parametrize(
        "subject",
        [
            "Security alert: new sign-in to your account",
            "Unusual sign-in activity detected",
            "New device sign-in from Chrome on Mac",
            "Suspicious activity on your account",
            "Security notice: new login detected",
        ],
    )
    def test_security_alert(self, subject: str) -> None:
        assert _classify_subject(subject) == DiscoveredAccountSourceType.SECURITY_ALERT

    # --- Newsletter ---
    @pytest.mark.parametrize(
        "subject",
        [
            "Your weekly reading digest from Medium",
            "The Substack newsletter — this week's picks",
            "Monthly update from the team",
        ],
    )
    def test_newsletter(self, subject: str) -> None:
        assert _classify_subject(subject) == DiscoveredAccountSourceType.NEWSLETTER

    # --- Other / unclassified ---
    @pytest.mark.parametrize(
        "subject",
        [
            "Re: meeting tomorrow",
            "Hello there",
            "Fwd: interesting article",
            "Out of office",
        ],
    )
    def test_other(self, subject: str) -> None:
        assert _classify_subject(subject) == DiscoveredAccountSourceType.OTHER

    def test_case_insensitive(self) -> None:
        assert (
            _classify_subject("WELCOME TO GITHUB")
            == DiscoveredAccountSourceType.ACCOUNT_CONFIRMATION
        )
        assert (
            _classify_subject("RESET YOUR PASSWORD")
            == DiscoveredAccountSourceType.PASSWORD_RESET
        )
