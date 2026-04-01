# tests/unit/modules/test_stealer_log_exposure.py
import uuid
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.modules.identity.stealer_log_exposure.service import (
    StealerLogExposureService,
)
from backend.app.providers.base.exceptions import ProviderError

SAMPLE_FINDING = {
    "provider": "hudson_rock",
    "category": "stealer_log_exposure",
    "title": "Stealer log hit: test@example.com",
    "description": "Stealer log hit for test@example.com. Date uploaded: 2024-01-15. OS: Windows 10. Malware: RedLine. Credentials found: 42 (passwords not shown).",
    "entity_type": "email",
    "entity_value": "test@example.com",
    "tags": ["stealer_log", "infostealer", "credential_theft"],
    "raw": {
        "date_uploaded": "2024-01-15",
        "computer_name": "DESKTOP-ABC123",
        "operating_system": "Windows 10",
        "malware_name": "RedLine",
        "credential_count": 42,
    },
}

SECOND_FINDING = {
    "provider": "hudson_rock",
    "category": "stealer_log_exposure",
    "title": "Stealer log hit: test@example.com",
    "description": "Stealer log hit for test@example.com. Date uploaded: 2024-03-20. OS: Windows 11. Malware: Vidar. Credentials found: 7 (passwords not shown).",
    "entity_type": "email",
    "entity_value": "test@example.com",
    "tags": ["stealer_log", "infostealer", "credential_theft"],
    "raw": {
        "date_uploaded": "2024-03-20",
        "computer_name": "LAPTOP-XYZ789",
        "operating_system": "Windows 11",
        "malware_name": "Vidar",
        "credential_count": 7,
    },
}


@pytest.mark.asyncio
async def test_run_emits_one_signal_per_stealer_entry() -> None:
    service = StealerLogExposureService()
    with (
        patch(
            "backend.app.modules.identity.stealer_log_exposure.service.HudsonRockProvider.get_compromised_data",
            return_value=[SAMPLE_FINDING, SECOND_FINDING],
        ),
        patch(
            "backend.app.modules.identity.stealer_log_exposure.service.settings",
            hudson_rock_api_key=SecretStr("test-api-key"),
        ),
    ):
        signals = await service.run(
            user_id=uuid.uuid4(),
            asset_id=uuid.uuid4(),
            asset_value="test@example.com",
        )
    assert len(signals) == 2


@pytest.mark.asyncio
async def test_run_returns_empty_list_when_no_stealers() -> None:
    service = StealerLogExposureService()
    with (
        patch(
            "backend.app.modules.identity.stealer_log_exposure.service.HudsonRockProvider.get_compromised_data",
            return_value=[],
        ),
        patch(
            "backend.app.modules.identity.stealer_log_exposure.service.settings",
            hudson_rock_api_key=SecretStr("test-api-key"),
        ),
    ):
        signals = await service.run(
            user_id=uuid.uuid4(),
            asset_id=uuid.uuid4(),
            asset_value="clean@example.com",
        )
    assert signals == []


@pytest.mark.asyncio
async def test_run_skips_silently_when_api_key_not_set() -> None:
    """No API key → return [] without raising."""
    service = StealerLogExposureService()
    with patch(
        "backend.app.modules.identity.stealer_log_exposure.service.settings",
        hudson_rock_api_key=None,
    ):
        signals = await service.run(
            user_id=uuid.uuid4(),
            asset_id=uuid.uuid4(),
            asset_value="test@example.com",
        )
    assert signals == []


@pytest.mark.asyncio
async def test_run_degrades_gracefully_on_provider_error() -> None:
    """ProviderError must not propagate — module returns [] instead."""
    service = StealerLogExposureService()
    with (
        patch(
            "backend.app.modules.identity.stealer_log_exposure.service.HudsonRockProvider.get_compromised_data",
            side_effect=ProviderError("Hudson Rock unavailable"),
        ),
        patch(
            "backend.app.modules.identity.stealer_log_exposure.service.settings",
            hudson_rock_api_key=SecretStr("test-api-key"),
        ),
    ):
        signals = await service.run(
            user_id=uuid.uuid4(),
            asset_id=uuid.uuid4(),
            asset_value="test@example.com",
        )
    assert signals == []


@pytest.mark.asyncio
async def test_signal_has_correct_fields() -> None:
    service = StealerLogExposureService()
    asset_id = uuid.uuid4()
    user_id = uuid.uuid4()
    with (
        patch(
            "backend.app.modules.identity.stealer_log_exposure.service.HudsonRockProvider.get_compromised_data",
            return_value=[SAMPLE_FINDING],
        ),
        patch(
            "backend.app.modules.identity.stealer_log_exposure.service.settings",
            hudson_rock_api_key=SecretStr("test-api-key"),
        ),
    ):
        signals = await service.run(
            user_id=user_id,
            asset_id=asset_id,
            asset_value="test@example.com",
        )
    assert len(signals) == 1
    sig = signals[0]
    assert sig.signal_type == "stealer_log_hit"
    assert sig.entity_type == EntityType.EMAIL
    assert sig.entity_id == asset_id
    assert sig.user_id == user_id
    assert sig.severity == Severity.CRITICAL
    assert sig.confidence == Confidence.HIGH
    assert sig.source == "stealer_log_exposure"
    assert sig.provider == "hudson_rock"


@pytest.mark.asyncio
async def test_source_ref_includes_date_for_dedup() -> None:
    """Each stealer entry gets a unique source_ref so different infection dates produce distinct signals."""
    service = StealerLogExposureService()
    with (
        patch(
            "backend.app.modules.identity.stealer_log_exposure.service.HudsonRockProvider.get_compromised_data",
            return_value=[SAMPLE_FINDING, SECOND_FINDING],
        ),
        patch(
            "backend.app.modules.identity.stealer_log_exposure.service.settings",
            hudson_rock_api_key=SecretStr("test-api-key"),
        ),
    ):
        signals = await service.run(
            user_id=uuid.uuid4(),
            asset_id=uuid.uuid4(),
            asset_value="test@example.com",
        )
    source_refs = [s.source_ref for s in signals]
    assert source_refs[0] == "hudson_rock:2024-01-15"
    assert source_refs[1] == "hudson_rock:2024-03-20"
    assert source_refs[0] != source_refs[1]


@pytest.mark.asyncio
async def test_evidence_does_not_include_passwords() -> None:
    """Password values must never appear in evidence dict."""
    service = StealerLogExposureService()
    with (
        patch(
            "backend.app.modules.identity.stealer_log_exposure.service.HudsonRockProvider.get_compromised_data",
            return_value=[SAMPLE_FINDING],
        ),
        patch(
            "backend.app.modules.identity.stealer_log_exposure.service.settings",
            hudson_rock_api_key=SecretStr("test-api-key"),
        ),
    ):
        signals = await service.run(
            user_id=uuid.uuid4(),
            asset_id=uuid.uuid4(),
            asset_value="test@example.com",
        )
    evidence = signals[0].evidence or {}
    assert "passwords" not in evidence
    assert "top_passwords" not in evidence
    assert "credentials" not in evidence
    assert evidence["credentials_count"] == 42
    assert evidence["stealer_family"] == "RedLine"
    assert evidence["computer_name"] == "DESKTOP-ABC123"
