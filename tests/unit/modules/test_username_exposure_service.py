# tests/unit/modules/test_username_exposure_service.py
import uuid
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from backend.app.core.enums import Severity
from backend.app.modules.identity.username_exposure.service import (
    UsernameExposureService,
    _emailcrawlr_severity,
)
from backend.app.providers.base.exceptions import ProviderError

USER_ID = uuid.uuid4()
ASSET_ID = uuid.uuid4()

EPIEOS_GOOGLE_FINDING = {
    "title": "Google Account",
    "description": "Email is linked to a Google account.",
    "raw": {"google_id": "123456789", "name": "Alice Example"},
}

EPIEOS_APPLE_FINDING = {
    "title": "Apple ID",
    "description": "Email is registered as an Apple ID.",
    "raw": {},
}


# ─── Severity helper ──────────────────────────────────────────────────────────


def test_emailcrawlr_severity_medium_baseline() -> None:
    assert _emailcrawlr_severity({}) == Severity.MEDIUM
    assert (
        _emailcrawlr_severity({"linkedin": "https://linkedin.com/in/alice"})
        == Severity.MEDIUM
    )


def test_emailcrawlr_severity_high_on_name() -> None:
    assert _emailcrawlr_severity({"name": "Alice Example"}) == Severity.HIGH


def test_emailcrawlr_severity_high_on_phone() -> None:
    assert _emailcrawlr_severity({"numbers": ["+1-555-0100"]}) == Severity.HIGH


def test_emailcrawlr_severity_high_on_location() -> None:
    assert _emailcrawlr_severity({"location": "New York, NY"}) == Severity.HIGH


# ─── No-op when no API keys configured ───────────────────────────────────────


@pytest.mark.asyncio
async def test_run_returns_empty_when_no_keys_configured() -> None:
    service = UsernameExposureService()
    with patch(
        "backend.app.modules.identity.username_exposure.service.settings"
    ) as mock_settings:
        mock_settings.epieos_api_key = None
        mock_settings.emailcrawlr_api_key = None
        mock_settings.gravatar_api_key = None

        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="alice@example.com",
        )

    assert signals == []


# ─── Epieos ───────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_emits_username_exposure_for_google_account() -> None:
    service = UsernameExposureService()
    with patch(
        "backend.app.modules.identity.username_exposure.service.settings"
    ) as mock_settings:
        mock_settings.epieos_api_key = SecretStr("test-key")
        mock_settings.emailcrawlr_api_key = None
        mock_settings.gravatar_api_key = None
        with patch(
            "backend.app.modules.identity.username_exposure.service.EpieosProvider.validate_email",
            return_value=[EPIEOS_GOOGLE_FINDING],
        ):
            signals = await service.run(
                user_id=USER_ID,
                asset_id=ASSET_ID,
                asset_value="alice@example.com",
            )

    assert len(signals) == 1
    s = signals[0]
    assert s.signal_type == "username_exposure"
    assert s.severity == Severity.INFO
    assert s.provider == "epieos"
    assert s.evidence["platform"] == "Google"
    assert s.evidence["username"] == "alice"


@pytest.mark.asyncio
async def test_run_emits_username_exposure_for_apple_account() -> None:
    service = UsernameExposureService()
    with patch(
        "backend.app.modules.identity.username_exposure.service.settings"
    ) as mock_settings:
        mock_settings.epieos_api_key = SecretStr("test-key")
        mock_settings.emailcrawlr_api_key = None
        mock_settings.gravatar_api_key = None
        with patch(
            "backend.app.modules.identity.username_exposure.service.EpieosProvider.validate_email",
            return_value=[EPIEOS_APPLE_FINDING],
        ):
            signals = await service.run(
                user_id=USER_ID,
                asset_id=ASSET_ID,
                asset_value="alice@example.com",
            )

    assert len(signals) == 1
    assert signals[0].evidence["platform"] == "Apple"


@pytest.mark.asyncio
async def test_run_graceful_on_epieos_failure() -> None:
    service = UsernameExposureService()
    with patch(
        "backend.app.modules.identity.username_exposure.service.settings"
    ) as mock_settings:
        mock_settings.epieos_api_key = SecretStr("test-key")
        mock_settings.emailcrawlr_api_key = None
        mock_settings.gravatar_api_key = None
        with patch(
            "backend.app.modules.identity.username_exposure.service.EpieosProvider.validate_email",
            side_effect=ProviderError("Epieos unavailable"),
        ):
            signals = await service.run(
                user_id=USER_ID,
                asset_id=ASSET_ID,
                asset_value="alice@example.com",
            )

    assert signals == []


# ─── EmailCrawlr ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_emits_email_public_exposure_from_emailcrawlr() -> None:
    service = UsernameExposureService()
    emailcrawlr_data = {
        "email": "alice@example.com",
        "name": "Alice Example",
        "location": "New York",
        "verified": True,
        "numbers": [],
    }
    with patch(
        "backend.app.modules.identity.username_exposure.service.settings"
    ) as mock_settings:
        mock_settings.epieos_api_key = None
        mock_settings.emailcrawlr_api_key = SecretStr("ec-key")
        mock_settings.gravatar_api_key = None
        with (
            patch(
                "backend.app.modules.identity.username_exposure.service.EmailcrawlrProvider.get_email",
                return_value=emailcrawlr_data,
            ),
            patch(
                "backend.app.modules.identity.username_exposure.service.EmailcrawlrProvider.search_emails",
                return_value=[],
            ),
        ):
            signals = await service.run(
                user_id=USER_ID,
                asset_id=ASSET_ID,
                asset_value="alice@example.com",
            )

    assert len(signals) == 1
    s = signals[0]
    assert s.signal_type == "email_public_exposure"
    assert s.severity == Severity.HIGH  # name + location present
    assert s.provider == "emailcrawlr"
    assert s.evidence["name"] == "Alice Example"


@pytest.mark.asyncio
async def test_run_emits_domain_exposure_signal_when_emails_found() -> None:
    service = UsernameExposureService()
    domain_findings = [
        {"entity_value": "bob@example.com"},
        {"entity_value": "carol@example.com"},
    ]
    with patch(
        "backend.app.modules.identity.username_exposure.service.settings"
    ) as mock_settings:
        mock_settings.epieos_api_key = None
        mock_settings.emailcrawlr_api_key = SecretStr("ec-key")
        mock_settings.gravatar_api_key = None
        with (
            patch(
                "backend.app.modules.identity.username_exposure.service.EmailcrawlrProvider.get_email",
                return_value={},
            ),
            patch(
                "backend.app.modules.identity.username_exposure.service.EmailcrawlrProvider.search_emails",
                return_value=domain_findings,
            ),
        ):
            signals = await service.run(
                user_id=USER_ID,
                asset_id=ASSET_ID,
                asset_value="alice@example.com",
            )

    assert len(signals) == 1
    s = signals[0]
    assert s.signal_type == "email_public_exposure"
    assert s.severity == Severity.MEDIUM
    assert s.evidence["domain"] == "example.com"
    assert s.evidence["email_count"] == 2


@pytest.mark.asyncio
async def test_run_graceful_on_emailcrawlr_failure() -> None:
    service = UsernameExposureService()
    with patch(
        "backend.app.modules.identity.username_exposure.service.settings"
    ) as mock_settings:
        mock_settings.epieos_api_key = None
        mock_settings.emailcrawlr_api_key = SecretStr("ec-key")
        mock_settings.gravatar_api_key = None
        with patch(
            "backend.app.modules.identity.username_exposure.service.EmailcrawlrProvider.get_email",
            side_effect=ProviderError("emailcrawlr down"),
        ):
            signals = await service.run(
                user_id=USER_ID,
                asset_id=ASSET_ID,
                asset_value="alice@example.com",
            )

    assert signals == []


# ─── Gravatar enrichment ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_attaches_gravatar_enrichment_to_all_signals() -> None:
    """Gravatar data must appear in evidence of every emitted signal."""
    service = UsernameExposureService()
    gravatar_profile = {
        "hash": "abc123",
        "display_name": "Alice Example",
        "profile_url": "https://gravatar.com/aliceexample",
        "verified_accounts": [],
        "links": [],
    }
    with patch(
        "backend.app.modules.identity.username_exposure.service.settings"
    ) as mock_settings:
        mock_settings.epieos_api_key = SecretStr("ep-key")
        mock_settings.emailcrawlr_api_key = None
        mock_settings.gravatar_api_key = SecretStr("gv-key")
        with (
            patch(
                "backend.app.modules.identity.username_exposure.service.EpieosProvider.validate_email",
                return_value=[EPIEOS_GOOGLE_FINDING, EPIEOS_APPLE_FINDING],
            ),
            patch(
                "backend.app.modules.identity.username_exposure.service.GravatarProvider.lookup",
                return_value=gravatar_profile,
            ),
        ):
            signals = await service.run(
                user_id=USER_ID,
                asset_id=ASSET_ID,
                asset_value="alice@example.com",
            )

    assert len(signals) == 2
    for signal in signals:
        assert "gravatar" in signal.evidence
        assert signal.evidence["gravatar"]["display_name"] == "Alice Example"


@pytest.mark.asyncio
async def test_run_skips_gravatar_when_no_signals_emitted() -> None:
    """Gravatar lookup should not run when there are no signals to enrich."""
    service = UsernameExposureService()
    with patch(
        "backend.app.modules.identity.username_exposure.service.settings"
    ) as mock_settings:
        mock_settings.epieos_api_key = None
        mock_settings.emailcrawlr_api_key = None
        mock_settings.gravatar_api_key = SecretStr("gv-key")
        with patch(
            "backend.app.modules.identity.username_exposure.service.GravatarProvider.lookup",
        ) as mock_gravatar:
            signals = await service.run(
                user_id=USER_ID,
                asset_id=ASSET_ID,
                asset_value="alice@example.com",
            )

    mock_gravatar.assert_not_called()
    assert signals == []


@pytest.mark.asyncio
async def test_run_graceful_on_gravatar_failure() -> None:
    """Gravatar ProviderError must not destroy already-emitted signals."""
    service = UsernameExposureService()
    with patch(
        "backend.app.modules.identity.username_exposure.service.settings"
    ) as mock_settings:
        mock_settings.epieos_api_key = SecretStr("ep-key")
        mock_settings.emailcrawlr_api_key = None
        mock_settings.gravatar_api_key = SecretStr("gv-key")
        with (
            patch(
                "backend.app.modules.identity.username_exposure.service.EpieosProvider.validate_email",
                return_value=[EPIEOS_GOOGLE_FINDING],
            ),
            patch(
                "backend.app.modules.identity.username_exposure.service.GravatarProvider.lookup",
                side_effect=ProviderError("Gravatar down"),
            ),
        ):
            signals = await service.run(
                user_id=USER_ID,
                asset_id=ASSET_ID,
                asset_value="alice@example.com",
            )

    # Signal still emitted; gravatar key absent from evidence
    assert len(signals) == 1
    assert "gravatar" not in signals[0].evidence
