# tests/unit/email_accounts/test_service_discovery.py
"""Unit tests for AccountDiscoveryService.classify_emails."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.email_accounts import DiscoveredAccountSourceType
from backend.app.db.repositories.service_registry import ServiceRegistryRepository
from backend.app.email_accounts.service import AccountDiscoveryService
from backend.app.providers.tools.mbox_parser.models import ParsedEmail

GITHUB_PASSWORD_RESET_URL = "https://github.com/password_reset"  # noqa: S105


def _make_email(
    *,
    sender_domain: str,
    subject: str | None = "Welcome to the service",
    from_address: str | None = None,
    date: datetime | None = None,
) -> ParsedEmail:
    return ParsedEmail(
        message_id="<test@example.com>",
        subject=subject,
        from_address=from_address or f"noreply@{sender_domain}",
        from_name="Test Sender",
        sender_domain=sender_domain,
        to_address="user@example.com",
        date=date or datetime(2024, 1, 1, tzinfo=UTC),
    )


def _make_service(
    service_name: str = "github.com",
    display_name: str = "GitHub",
    login_url: str = "https://github.com/login",
    password_reset_url: str = GITHUB_PASSWORD_RESET_URL,
) -> MagicMock:
    entry = MagicMock()
    entry.service_name = service_name
    entry.display_name = display_name
    entry.login_url = login_url
    entry.password_reset_url = password_reset_url
    return entry


@pytest.fixture
def mock_session() -> MagicMock:
    return MagicMock(spec=AsyncSession)


@pytest.mark.asyncio
async def test_empty_email_list_returns_empty(mock_session: MagicMock) -> None:
    service = AccountDiscoveryService(mock_session)
    result = await service.classify_emails([], "user@example.com")
    assert result == []


@pytest.mark.asyncio
async def test_skip_domains_are_filtered(mock_session: MagicMock) -> None:
    """Emails from generic providers (gmail, outlook, etc.) are always skipped."""
    skip_domain_samples = [
        "gmail.com",
        "outlook.com",
        "yahoo.com",
        "icloud.com",
        "protonmail.com",
    ]
    emails = [_make_email(sender_domain=d) for d in skip_domain_samples]

    with patch.object(
        ServiceRegistryRepository, "find_by_domain", new_callable=AsyncMock
    ) as mock_find:
        service = AccountDiscoveryService(mock_session)
        result = await service.classify_emails(emails, "user@example.com")

    assert result == []
    mock_find.assert_not_called()


@pytest.mark.asyncio
async def test_other_with_no_registry_match_is_skipped(mock_session: MagicMock) -> None:
    """Unclassified emails with no registry entry are dropped."""
    emails = [
        _make_email(sender_domain="unknownservice.io", subject="Re: your question")
    ]

    with patch.object(
        ServiceRegistryRepository, "find_by_domain", new_callable=AsyncMock
    ) as mock_find:
        mock_find.return_value = None
        service = AccountDiscoveryService(mock_session)
        result = await service.classify_emails(emails, "user@example.com")

    assert result == []


@pytest.mark.asyncio
async def test_other_with_registry_match_is_kept(mock_session: MagicMock) -> None:
    """Generic-subject email from a known service IS kept."""
    emails = [_make_email(sender_domain="slack.com", subject="Re: thread in #general")]

    with patch.object(
        ServiceRegistryRepository, "find_by_domain", new_callable=AsyncMock
    ) as mock_find:
        mock_find.return_value = _make_service(
            "slack.com", "Slack", "https://slack.com/signin", None
        )
        service = AccountDiscoveryService(mock_session)
        result = await service.classify_emails(emails, "user@example.com")

    assert len(result) == 1
    assert result[0].service_name == "slack.com"
    assert result[0].display_name == "Slack"


@pytest.mark.asyncio
async def test_account_confirmation_without_registry_falls_back_to_domain(
    mock_session: MagicMock,
) -> None:
    """Account-confirmation email from unknown service → domain-derived name."""
    emails = [
        _make_email(sender_domain="newstartup.io", subject="Welcome to NewStartup!")
    ]

    with patch.object(
        ServiceRegistryRepository, "find_by_domain", new_callable=AsyncMock
    ) as mock_find:
        mock_find.return_value = None
        service = AccountDiscoveryService(mock_session)
        result = await service.classify_emails(emails, "user@example.com")

    assert len(result) == 1
    assert result[0].service_name == "newstartup.io"
    assert result[0].display_name == "newstartup.io"
    assert result[0].login_url is None
    assert result[0].source_type == DiscoveredAccountSourceType.ACCOUNT_CONFIRMATION


@pytest.mark.asyncio
async def test_registry_entry_populates_urls(mock_session: MagicMock) -> None:
    """When a registry entry is found, its URLs override fallback values."""
    emails = [_make_email(sender_domain="github.com", subject="Welcome to GitHub")]

    registry_entry = _make_service(
        service_name="github.com",
        display_name="GitHub",
        login_url="https://github.com/login",
        password_reset_url=GITHUB_PASSWORD_RESET_URL,
    )
    with patch.object(
        ServiceRegistryRepository, "find_by_domain", new_callable=AsyncMock
    ) as mock_find:
        mock_find.return_value = registry_entry
        service = AccountDiscoveryService(mock_session)
        result = await service.classify_emails(emails, "user@example.com")

    assert len(result) == 1
    assert result[0].login_url == "https://github.com/login"
    assert result[0].password_reset_url == GITHUB_PASSWORD_RESET_URL


@pytest.mark.asyncio
async def test_recipient_email_is_passed_through(mock_session: MagicMock) -> None:
    """email_used on drafts must equal the recipient_email argument."""
    emails = [_make_email(sender_domain="spotify.com", subject="Welcome to Spotify")]

    with patch.object(
        ServiceRegistryRepository, "find_by_domain", new_callable=AsyncMock
    ) as mock_find:
        mock_find.return_value = None
        service = AccountDiscoveryService(mock_session)
        result = await service.classify_emails(emails, "alice@example.com")

    assert len(result) == 1
    assert result[0].email_used == "alice@example.com"


@pytest.mark.asyncio
async def test_sender_domain_stored_on_draft(mock_session: MagicMock) -> None:
    emails = [
        _make_email(sender_domain="dropbox.com", subject="Confirm your Dropbox account")
    ]

    with patch.object(
        ServiceRegistryRepository, "find_by_domain", new_callable=AsyncMock
    ) as mock_find:
        mock_find.return_value = None
        service = AccountDiscoveryService(mock_session)
        result = await service.classify_emails(emails, "user@example.com")

    assert result[0].sender_domain == "dropbox.com"


@pytest.mark.asyncio
async def test_password_reset_subject_is_classified(mock_session: MagicMock) -> None:
    emails = [
        _make_email(sender_domain="stripe.com", subject="Reset your Stripe password")
    ]

    with patch.object(
        ServiceRegistryRepository, "find_by_domain", new_callable=AsyncMock
    ) as mock_find:
        mock_find.return_value = None
        service = AccountDiscoveryService(mock_session)
        result = await service.classify_emails(emails, "user@example.com")

    assert len(result) == 1
    assert result[0].source_type == DiscoveredAccountSourceType.PASSWORD_RESET


@pytest.mark.asyncio
async def test_multiple_domains_produce_multiple_drafts(
    mock_session: MagicMock,
) -> None:
    emails = [
        _make_email(sender_domain="github.com", subject="Welcome to GitHub"),
        _make_email(
            sender_domain="netflix.com", subject="Confirm your Netflix account"
        ),
        _make_email(sender_domain="spotify.com", subject="Thanks for joining Spotify"),
    ]

    with patch.object(
        ServiceRegistryRepository, "find_by_domain", new_callable=AsyncMock
    ) as mock_find:
        mock_find.return_value = None
        service = AccountDiscoveryService(mock_session)
        result = await service.classify_emails(emails, "user@example.com")

    assert len(result) == 3
    domains = {r.sender_domain for r in result}
    assert domains == {"github.com", "netflix.com", "spotify.com"}


@pytest.mark.asyncio
async def test_null_domain_is_skipped(mock_session: MagicMock) -> None:
    """Emails with no parseable sender domain are skipped silently."""
    email = ParsedEmail(
        message_id="<x@y>",
        subject="Welcome!",
        from_address=None,
        from_name=None,
        sender_domain=None,
        to_address=None,
        date=None,
    )
    with patch.object(
        ServiceRegistryRepository, "find_by_domain", new_callable=AsyncMock
    ):
        service = AccountDiscoveryService(mock_session)
        result = await service.classify_emails([email], "user@example.com")

    assert result == []


@pytest.mark.asyncio
async def test_date_propagated_to_draft(mock_session: MagicMock) -> None:
    ts = datetime(2024, 6, 15, 12, 0, 0, tzinfo=UTC)
    emails = [
        _make_email(sender_domain="notion.so", subject="Welcome to Notion", date=ts)
    ]

    with patch.object(
        ServiceRegistryRepository, "find_by_domain", new_callable=AsyncMock
    ) as mock_find:
        mock_find.return_value = None
        service = AccountDiscoveryService(mock_session)
        result = await service.classify_emails(emails, "user@example.com")

    assert result[0].first_seen_at == ts
    assert result[0].last_seen_at == ts
