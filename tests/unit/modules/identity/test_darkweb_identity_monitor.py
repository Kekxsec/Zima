# tests/unit/modules/identity/test_darkweb_identity_monitor.py
import uuid
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from backend.app.core.enums import EntityType, Severity
from backend.app.modules.identity.darkweb_identity_monitor.service import (
    DarkwebIdentityMonitorService,
)
from backend.app.providers.base.exceptions import ProviderError

USER_ID = uuid.uuid4()
ASSET_ID = uuid.uuid4()


def _finding(media: int = 0, storageid: str = "abc123") -> dict:  # type: ignore[type-arg]
    return {
        "title": "Dark web record found",
        "description": "Found in a dark web paste",
        "tags": ["darkweb"],
        "raw": {
            "media": media,
            "storageid": storageid,
            "bucket": "darknet",
            "date": "2024-01-01",
            "name": "leak.txt",
        },
    }


@pytest.mark.asyncio
async def test_skips_when_no_intelx_key() -> None:
    service = DarkwebIdentityMonitorService()
    with patch(
        "backend.app.modules.identity.darkweb_identity_monitor.service.settings"
    ) as mock_settings:
        mock_settings.intelx_api_key = None
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="victim@example.com",
        )
    assert outcome.signals == []


@pytest.mark.asyncio
async def test_emits_critical_signal_for_media_type_1() -> None:
    service = DarkwebIdentityMonitorService()
    with (
        patch(
            "backend.app.modules.identity.darkweb_identity_monitor.service.settings"
        ) as mock_settings,
        patch(
            "backend.app.modules.identity.darkweb_identity_monitor.service.IntelXProvider.search",
            return_value=[_finding(media=1)],
        ),
    ):
        mock_settings.intelx_api_key = SecretStr("test-key")
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="victim@example.com",
        )

    assert len(outcome.signals) == 1
    s = outcome.signals[0]
    assert s.signal_type == "darkweb_identity_exposure"
    assert s.severity == Severity.CRITICAL
    assert s.entity_type == EntityType.EMAIL
    assert s.provider == "intelx"
    assert s.evidence["has_credentials"] is True
    assert s.evidence["media_type"] == 1


@pytest.mark.asyncio
async def test_emits_critical_signal_for_media_type_13() -> None:
    service = DarkwebIdentityMonitorService()
    with (
        patch(
            "backend.app.modules.identity.darkweb_identity_monitor.service.settings"
        ) as mock_settings,
        patch(
            "backend.app.modules.identity.darkweb_identity_monitor.service.IntelXProvider.search",
            return_value=[_finding(media=13)],
        ),
    ):
        mock_settings.intelx_api_key = SecretStr("test-key")
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="victim@example.com",
        )

    assert len(outcome.signals) == 1
    assert outcome.signals[0].severity == Severity.CRITICAL
    assert outcome.signals[0].evidence["has_credentials"] is True


@pytest.mark.asyncio
async def test_emits_high_signal_for_non_credential_media_type() -> None:
    service = DarkwebIdentityMonitorService()
    with (
        patch(
            "backend.app.modules.identity.darkweb_identity_monitor.service.settings"
        ) as mock_settings,
        patch(
            "backend.app.modules.identity.darkweb_identity_monitor.service.IntelXProvider.search",
            return_value=[_finding(media=2)],
        ),
    ):
        mock_settings.intelx_api_key = SecretStr("test-key")
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="victim@example.com",
        )

    assert len(outcome.signals) == 1
    s = outcome.signals[0]
    assert s.severity == Severity.HIGH
    assert s.evidence["has_credentials"] is False


@pytest.mark.asyncio
async def test_returns_empty_on_provider_failure() -> None:
    service = DarkwebIdentityMonitorService()
    with (
        patch(
            "backend.app.modules.identity.darkweb_identity_monitor.service.settings"
        ) as mock_settings,
        patch(
            "backend.app.modules.identity.darkweb_identity_monitor.service.IntelXProvider.search",
            side_effect=ProviderError("IntelX unavailable"),
        ),
    ):
        mock_settings.intelx_api_key = SecretStr("test-key")
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="victim@example.com",
        )

    assert outcome.signals == []


@pytest.mark.asyncio
async def test_emits_multiple_signals_for_multiple_findings() -> None:
    service = DarkwebIdentityMonitorService()
    with (
        patch(
            "backend.app.modules.identity.darkweb_identity_monitor.service.settings"
        ) as mock_settings,
        patch(
            "backend.app.modules.identity.darkweb_identity_monitor.service.IntelXProvider.search",
            return_value=[
                _finding(media=1, storageid="id1"),
                _finding(media=2, storageid="id2"),
                _finding(media=13, storageid="id3"),
            ],
        ),
    ):
        mock_settings.intelx_api_key = SecretStr("test-key")
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="victim@example.com",
        )

    assert len(outcome.signals) == 3
    severities = {s.severity for s in outcome.signals}
    assert Severity.CRITICAL in severities
    assert Severity.HIGH in severities
