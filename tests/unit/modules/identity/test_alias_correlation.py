# tests/unit/modules/identity/test_alias_correlation.py
import uuid
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from backend.app.core.enums import EntityType, Severity
from backend.app.modules.identity.alias_correlation.service import (
    AliasCorrelationService,
)
from backend.app.providers.base.exceptions import ProviderError

USER_ID = uuid.uuid4()
ASSET_ID = uuid.uuid4()

EPIEOS_GOOGLE_WITH_NAME = {
    "title": "Google Account",
    "description": "Email linked to Google account with real name.",
    "raw": {"name": "Alice Example", "google_id": "111"},
}

EPIEOS_GOOGLE_NO_NAME = {
    "title": "Google Account",
    "description": "Email linked to Google account, no name.",
    "raw": {"google_id": "222"},
}

EPIEOS_NON_GOOGLE = {
    "title": "Apple ID",
    "description": "Apple account found.",
    "raw": {"some": "data"},
}

EMAILFORMAT_RESULTS = [
    {"email": "first.last@example.com", "domain": "example.com"},
    {"email": "f.last@example.com", "domain": "example.com"},
]


@pytest.mark.asyncio
async def test_run_returns_empty_when_no_epieos_key() -> None:
    service = AliasCorrelationService()
    with patch(
        "backend.app.modules.identity.alias_correlation.service.settings"
    ) as mock_settings:
        mock_settings.epieos_api_key = None

        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="alice@example.com",
        )

    assert signals == []


@pytest.mark.asyncio
async def test_run_emits_alias_signal_when_google_name_found() -> None:
    service = AliasCorrelationService()
    with patch(
        "backend.app.modules.identity.alias_correlation.service.settings"
    ) as mock_settings:
        mock_settings.epieos_api_key = SecretStr("test-key")
        with (
            patch(
                "backend.app.modules.identity.alias_correlation.service.EpieosProvider.validate_email",
                return_value=[EPIEOS_GOOGLE_WITH_NAME],
            ),
            patch(
                "backend.app.modules.identity.alias_correlation.service.EmailformatProvider.get_formats",
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
    assert s.signal_type == "alias_exposure_detected"
    assert s.entity_type == EntityType.EMAIL
    assert s.provider == "epieos"
    assert s.evidence["alias_detected"] is True
    assert s.evidence["platform"] == "Google"
    assert s.severity == Severity.LOW


@pytest.mark.asyncio
async def test_run_skips_google_finding_without_name() -> None:
    """No alias signal when the Google raw payload has no 'name' field."""
    service = AliasCorrelationService()
    with patch(
        "backend.app.modules.identity.alias_correlation.service.settings"
    ) as mock_settings:
        mock_settings.epieos_api_key = SecretStr("test-key")
        with (
            patch(
                "backend.app.modules.identity.alias_correlation.service.EpieosProvider.validate_email",
                return_value=[EPIEOS_GOOGLE_NO_NAME],
            ),
            patch(
                "backend.app.modules.identity.alias_correlation.service.EmailformatProvider.get_formats",
                return_value=[],
            ),
        ):
            signals = await service.run(
                user_id=USER_ID,
                asset_id=ASSET_ID,
                asset_value="alice@example.com",
            )

    assert signals == []


@pytest.mark.asyncio
async def test_run_skips_non_google_findings() -> None:
    service = AliasCorrelationService()
    with patch(
        "backend.app.modules.identity.alias_correlation.service.settings"
    ) as mock_settings:
        mock_settings.epieos_api_key = SecretStr("test-key")
        with (
            patch(
                "backend.app.modules.identity.alias_correlation.service.EpieosProvider.validate_email",
                return_value=[EPIEOS_NON_GOOGLE],
            ),
            patch(
                "backend.app.modules.identity.alias_correlation.service.EmailformatProvider.get_formats",
                return_value=[],
            ),
        ):
            signals = await service.run(
                user_id=USER_ID,
                asset_id=ASSET_ID,
                asset_value="alice@example.com",
            )

    assert signals == []


@pytest.mark.asyncio
async def test_run_attaches_emailformat_patterns_to_evidence() -> None:
    service = AliasCorrelationService()
    with patch(
        "backend.app.modules.identity.alias_correlation.service.settings"
    ) as mock_settings:
        mock_settings.epieos_api_key = SecretStr("test-key")
        with (
            patch(
                "backend.app.modules.identity.alias_correlation.service.EpieosProvider.validate_email",
                return_value=[EPIEOS_GOOGLE_WITH_NAME],
            ),
            patch(
                "backend.app.modules.identity.alias_correlation.service.EmailformatProvider.get_formats",
                return_value=EMAILFORMAT_RESULTS,
            ),
        ):
            signals = await service.run(
                user_id=USER_ID,
                asset_id=ASSET_ID,
                asset_value="alice@example.com",
            )

    assert len(signals) == 1
    assert "emailformat_patterns" in signals[0].evidence
    assert len(signals[0].evidence["emailformat_patterns"]) == 2
    assert (
        signals[0].evidence["emailformat_patterns"][0]["email"]
        == "first.last@example.com"
    )


@pytest.mark.asyncio
async def test_run_evidence_has_no_emailformat_key_when_no_patterns() -> None:
    """emailformat_patterns key must be absent (not empty list) when nothing found."""
    service = AliasCorrelationService()
    with patch(
        "backend.app.modules.identity.alias_correlation.service.settings"
    ) as mock_settings:
        mock_settings.epieos_api_key = SecretStr("test-key")
        with (
            patch(
                "backend.app.modules.identity.alias_correlation.service.EpieosProvider.validate_email",
                return_value=[EPIEOS_GOOGLE_WITH_NAME],
            ),
            patch(
                "backend.app.modules.identity.alias_correlation.service.EmailformatProvider.get_formats",
                return_value=[],
            ),
        ):
            signals = await service.run(
                user_id=USER_ID,
                asset_id=ASSET_ID,
                asset_value="alice@example.com",
            )

    assert "emailformat_patterns" not in signals[0].evidence


@pytest.mark.asyncio
async def test_run_graceful_on_epieos_failure() -> None:
    service = AliasCorrelationService()
    with patch(
        "backend.app.modules.identity.alias_correlation.service.settings"
    ) as mock_settings:
        mock_settings.epieos_api_key = SecretStr("test-key")
        with (
            patch(
                "backend.app.modules.identity.alias_correlation.service.EpieosProvider.validate_email",
                side_effect=ProviderError("Epieos unavailable"),
            ),
        ):
            signals = await service.run(
                user_id=USER_ID,
                asset_id=ASSET_ID,
                asset_value="alice@example.com",
            )

    assert signals == []


@pytest.mark.asyncio
async def test_run_graceful_on_emailformat_failure() -> None:
    """Emailformat failure must not block alias signals from being emitted."""
    service = AliasCorrelationService()
    with patch(
        "backend.app.modules.identity.alias_correlation.service.settings"
    ) as mock_settings:
        mock_settings.epieos_api_key = SecretStr("test-key")
        with (
            patch(
                "backend.app.modules.identity.alias_correlation.service.EpieosProvider.validate_email",
                return_value=[EPIEOS_GOOGLE_WITH_NAME],
            ),
            patch(
                "backend.app.modules.identity.alias_correlation.service.EmailformatProvider.get_formats",
                side_effect=ProviderError("emailformat.com unreachable"),
            ),
        ):
            signals = await service.run(
                user_id=USER_ID,
                asset_id=ASSET_ID,
                asset_value="alice@example.com",
            )

    # Signal emitted; emailformat enrichment absent but no crash
    assert len(signals) == 1
    assert "emailformat_patterns" not in signals[0].evidence
