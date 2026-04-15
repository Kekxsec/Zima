# tests/unit/modules/identity/test_alias_correlation.py
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.core.enums import EntityType, Severity
from backend.app.modules.identity.alias_correlation.service import (
    AliasCorrelationService,
)
from backend.app.providers.base.models import ProviderResult

USER_ID = uuid.uuid4()
ASSET_ID = uuid.uuid4()


def _wmn_result(findings: list) -> ProviderResult:
    return ProviderResult(provider="tool_whatsmyname", success=True, findings=findings)


def _wmn_empty() -> ProviderResult:
    return ProviderResult(provider="tool_whatsmyname", success=True, findings=[])


def _wmn_failed() -> ProviderResult:
    return ProviderResult(provider="tool_whatsmyname", success=False, findings=[])


@pytest.mark.asyncio
async def test_run_returns_empty_when_empty_username() -> None:
    """Email with empty local part (pathological input) returns no signals."""
    service = AliasCorrelationService()
    outcome = await service.run(
        user_id=USER_ID,
        asset_id=ASSET_ID,
        asset_value="@example.com",
    )
    assert outcome.signals == []


@pytest.mark.asyncio
async def test_run_returns_empty_when_no_findings() -> None:
    """No signals emitted when WhatsmyName finds nothing."""
    service = AliasCorrelationService()
    with patch(
        "backend.app.modules.identity.alias_correlation.service.run_provider",
        new=AsyncMock(return_value=_wmn_empty()),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="alice@example.com",
        )
    assert outcome.signals == []


@pytest.mark.asyncio
async def test_run_emits_alias_signal_for_each_finding() -> None:
    """One signal per platform found by WhatsmyName."""
    findings = [
        {
            "title": "GitHub",
            "description": "Username found on GitHub.",
            "raw": {"site": "GitHub", "url": "https://github.com/alice"},
        },
        {
            "title": "Twitter",
            "description": "Username found on Twitter.",
            "raw": {"site": "Twitter", "url": "https://twitter.com/alice"},
        },
    ]
    service = AliasCorrelationService()
    with patch(
        "backend.app.modules.identity.alias_correlation.service.run_provider",
        new=AsyncMock(return_value=_wmn_result(findings)),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="alice@example.com",
        )

    assert len(outcome.signals) == 2
    for s in outcome.signals:
        assert s.signal_type == "alias_exposure_detected"
        assert s.entity_type == EntityType.EMAIL
        assert s.severity == Severity.LOW
        assert s.source == "alias_correlation"
        assert s.provider == "tool_whatsmyname"
        assert s.evidence["alias_detected"] is True
        assert s.evidence["username"] == "alice"


@pytest.mark.asyncio
async def test_run_extracts_platform_from_raw_site() -> None:
    """Platform name comes from raw['site'] when present."""
    findings = [
        {
            "title": "unused",
            "raw": {"site": "LinkedIn", "url": "https://linkedin.com/in/alice"},
        },
    ]
    service = AliasCorrelationService()
    with patch(
        "backend.app.modules.identity.alias_correlation.service.run_provider",
        new=AsyncMock(return_value=_wmn_result(findings)),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="alice@example.com",
        )
    assert outcome.signals[0].evidence["platform"] == "LinkedIn"
    assert outcome.signals[0].evidence["profile_url"] == "https://linkedin.com/in/alice"


@pytest.mark.asyncio
async def test_run_falls_back_to_title_when_no_raw_site() -> None:
    """Platform name falls back to title when raw has no 'site' key."""
    findings = [
        {"title": "Username found: Mastodon", "raw": {}},
    ]
    service = AliasCorrelationService()
    with patch(
        "backend.app.modules.identity.alias_correlation.service.run_provider",
        new=AsyncMock(return_value=_wmn_result(findings)),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="alice@example.com",
        )
    assert outcome.signals[0].evidence["platform"] == "Mastodon"


@pytest.mark.asyncio
async def test_run_graceful_on_provider_failure() -> None:
    """Provider failure results in zero signals, not an exception."""
    service = AliasCorrelationService()
    with patch(
        "backend.app.modules.identity.alias_correlation.service.run_provider",
        new=AsyncMock(return_value=_wmn_failed()),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="alice@example.com",
        )
    assert outcome.signals == []
