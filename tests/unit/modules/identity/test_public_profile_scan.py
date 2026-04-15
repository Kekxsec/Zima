# tests/unit/modules/identity/test_public_profile_scan.py
import uuid
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from backend.app.core.enums import EntityType, Severity
from backend.app.modules.identity.public_profile_scan.service import (
    PublicProfileScanService,
)
from backend.app.providers.base.exceptions import ProviderError

USER_ID = uuid.uuid4()
ASSET_ID = uuid.uuid4()


def _gravatar_profile(
    display_name: str = "John Doe",
    profile_url: str = "https://gravatar.com/johndoe",
    hash_: str = "abc123",
) -> dict:  # type: ignore[type-arg]
    return {
        "display_name": display_name,
        "profile_url": profile_url,
        "avatar_url": "https://gravatar.com/avatar/abc123",
        "location": "London",
        "hash": hash_,
        "verified_accounts": [],
    }


@pytest.mark.asyncio
async def test_gravatar_profile_with_display_name_emits_signal() -> None:
    service = PublicProfileScanService()
    with (
        patch(
            "backend.app.modules.identity.public_profile_scan.service.settings"
        ) as mock_settings,
        patch(
            "backend.app.modules.identity.public_profile_scan.service.GravatarProvider.lookup",
            return_value=_gravatar_profile(),
        ),
    ):
        mock_settings.gravatar_api_key = SecretStr("grav-key")
        mock_settings.emailcrawlr_api_key = None
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="user@example.com",
        )

    assert len(outcome.signals) == 1
    s = outcome.signals[0]
    assert s.signal_type == "public_profile_exposure"
    assert s.severity == Severity.LOW
    assert s.provider == "gravatar"
    assert s.entity_type == EntityType.EMAIL
    assert s.evidence["display_name"] == "John Doe"


@pytest.mark.asyncio
async def test_gravatar_profile_url_only_emits_signal() -> None:
    service = PublicProfileScanService()
    with (
        patch(
            "backend.app.modules.identity.public_profile_scan.service.settings"
        ) as mock_settings,
        patch(
            "backend.app.modules.identity.public_profile_scan.service.GravatarProvider.lookup",
            return_value=_gravatar_profile(display_name=""),
        ),
    ):
        mock_settings.gravatar_api_key = SecretStr("grav-key")
        mock_settings.emailcrawlr_api_key = None
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="user@example.com",
        )

    assert len(outcome.signals) == 1
    assert outcome.signals[0].provider == "gravatar"


@pytest.mark.asyncio
async def test_gravatar_no_name_or_url_emits_no_signal() -> None:
    service = PublicProfileScanService()
    with (
        patch(
            "backend.app.modules.identity.public_profile_scan.service.settings"
        ) as mock_settings,
        patch(
            "backend.app.modules.identity.public_profile_scan.service.GravatarProvider.lookup",
            return_value=_gravatar_profile(display_name="", profile_url=""),
        ),
    ):
        mock_settings.gravatar_api_key = SecretStr("grav-key")
        mock_settings.emailcrawlr_api_key = None
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="nobody@example.com",
        )

    assert outcome.signals == []


@pytest.mark.asyncio
async def test_gravatar_provider_failure_returns_empty() -> None:
    service = PublicProfileScanService()
    with (
        patch(
            "backend.app.modules.identity.public_profile_scan.service.settings"
        ) as mock_settings,
        patch(
            "backend.app.modules.identity.public_profile_scan.service.GravatarProvider.lookup",
            side_effect=ProviderError("Gravatar unreachable"),
        ),
    ):
        mock_settings.gravatar_api_key = SecretStr("grav-key")
        mock_settings.emailcrawlr_api_key = None
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="user@example.com",
        )

    assert outcome.signals == []


@pytest.mark.asyncio
async def test_emailcrawlr_emits_signal_when_social_data_found() -> None:
    service = PublicProfileScanService()
    with (
        patch(
            "backend.app.modules.identity.public_profile_scan.service.settings"
        ) as mock_settings,
        patch(
            "backend.app.modules.identity.public_profile_scan.service.GravatarProvider.lookup",
            return_value=_gravatar_profile(display_name="", profile_url=""),
        ),
        patch(
            "backend.app.modules.identity.public_profile_scan.service.EmailcrawlrProvider.get_email",
            return_value={
                "name": "Jane Smith",
                "linkedin": "https://linkedin.com/in/janesmith",
                "twitter": "",
                "references": 3,
                "job_title": "Engineer",
                "location": "NYC",
            },
        ),
    ):
        mock_settings.gravatar_api_key = SecretStr("grav-key")
        mock_settings.emailcrawlr_api_key = SecretStr("ecrawlr-key")
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="jane@example.com",
        )

    assert len(outcome.signals) == 1
    s = outcome.signals[0]
    assert s.provider == "emailcrawlr"
    assert s.evidence["name"] == "Jane Smith"
    assert s.evidence["linkedin"] == "https://linkedin.com/in/janesmith"


@pytest.mark.asyncio
async def test_emailcrawlr_skipped_when_no_key() -> None:
    service = PublicProfileScanService()
    with (
        patch(
            "backend.app.modules.identity.public_profile_scan.service.settings"
        ) as mock_settings,
        patch(
            "backend.app.modules.identity.public_profile_scan.service.GravatarProvider.lookup",
            return_value=_gravatar_profile(display_name="", profile_url=""),
        ),
    ):
        mock_settings.gravatar_api_key = SecretStr("grav-key")
        mock_settings.emailcrawlr_api_key = None
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="user@example.com",
        )

    assert outcome.signals == []


@pytest.mark.asyncio
async def test_emailcrawlr_failure_logged_not_raised() -> None:
    service = PublicProfileScanService()
    with (
        patch(
            "backend.app.modules.identity.public_profile_scan.service.settings"
        ) as mock_settings,
        patch(
            "backend.app.modules.identity.public_profile_scan.service.GravatarProvider.lookup",
            return_value=_gravatar_profile(display_name="", profile_url=""),
        ),
        patch(
            "backend.app.modules.identity.public_profile_scan.service.EmailcrawlrProvider.get_email",
            side_effect=ProviderError("EmailCrawlr down"),
        ),
    ):
        mock_settings.gravatar_api_key = SecretStr("grav-key")
        mock_settings.emailcrawlr_api_key = SecretStr("ecrawlr-key")
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="user@example.com",
        )

    assert outcome.signals == []
