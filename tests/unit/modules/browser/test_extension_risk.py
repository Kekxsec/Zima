# tests/unit/modules/browser/test_extension_risk.py
import uuid
from unittest.mock import patch

import pytest

from backend.app.core.enums import EntityType, Severity
from backend.app.modules.browser.extension_risk.rules import crxcavator_severity
from backend.app.modules.browser.extension_risk.service import ExtensionRiskService
from backend.app.providers.base.exceptions import ProviderError

USER_ID = uuid.uuid4()
ASSET_ID = uuid.uuid4()

# Minimal CRXcavator report structure
CRX_REPORT = {
    "data": {
        "risk": {
            "total": 500,
            "csp": {"total": 120},
            "permissions": {"total": 200},
            "retire": {"total": 100},
            "webstore": {"total": 80},
        }
    }
}

CRX_REPORT_LOW = {
    "data": {
        "risk": {
            "total": 200,
            "csp": {"total": 50},
            "permissions": {"total": 80},
            "retire": {"total": 30},
            "webstore": {"total": 40},
        }
    }
}


# ─── Rules ────────────────────────────────────────────────────────────────────


def test_crxcavator_severity_low() -> None:
    assert crxcavator_severity(0) == Severity.LOW
    assert crxcavator_severity(377) == Severity.LOW


def test_crxcavator_severity_medium() -> None:
    assert crxcavator_severity(378) == Severity.MEDIUM
    assert crxcavator_severity(478) == Severity.MEDIUM


def test_crxcavator_severity_high() -> None:
    assert crxcavator_severity(479) == Severity.HIGH
    assert crxcavator_severity(1000) == Severity.HIGH


# ─── Service ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_emits_signal_for_known_extension() -> None:
    service = ExtensionRiskService()
    with (
        patch(
            "backend.app.modules.browser.extension_risk.service.CrxcavatorProvider.check_extension",
            return_value=CRX_REPORT,
        ),
        patch(
            "backend.app.modules.browser.extension_risk.service.ChromeWebStoreApiProvider.get_extension",
            return_value={"id": "cfhdojbkjhnklbpkdaibdccddilifddb", "name": "AdBlock"},
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="cfhdojbkjhnklbpkdaibdccddilifddb:1.2.3:Chrome",
        )

    assert len(outcome.signals) == 1
    s = outcome.signals[0]
    assert s.signal_type == "browser_extension_risk"
    assert s.severity == Severity.HIGH  # total_risk=500 > 478
    assert s.entity_type == EntityType.URL
    assert s.provider == "crxcavator"
    assert s.evidence["total_risk"] == 500
    assert s.evidence["extension_id"] == "cfhdojbkjhnklbpkdaibdccddilifddb"


@pytest.mark.asyncio
async def test_run_resolves_latest_version() -> None:
    """When version='latest', get_versions is called first then check_extension."""
    service = ExtensionRiskService()
    with (
        patch(
            "backend.app.modules.browser.extension_risk.service.CrxcavatorProvider.get_versions",
            return_value=[{"version": "1.0.0"}, {"version": "2.0.0"}],
        ) as mock_versions,
        patch(
            "backend.app.modules.browser.extension_risk.service.CrxcavatorProvider.check_extension",
            return_value=CRX_REPORT_LOW,
        ) as mock_check,
        patch(
            "backend.app.modules.browser.extension_risk.service.ChromeWebStoreApiProvider.get_extension",
            return_value=None,
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="abcdefghijklmnopabcdefghijklmnop",  # 32-char id → latest + Chrome
        )

    mock_versions.assert_called_once_with("abcdefghijklmnopabcdefghijklmnop")
    mock_check.assert_called_once_with(
        "abcdefghijklmnopabcdefghijklmnop", "2.0.0", "Chrome"
    )
    assert len(outcome.signals) == 1
    assert outcome.signals[0].severity == Severity.LOW  # total_risk=200 ≤ 377


@pytest.mark.asyncio
async def test_run_returns_empty_when_no_crxcavator_report() -> None:
    """No CRXcavator report → no signal emitted."""
    service = ExtensionRiskService()
    with (
        patch(
            "backend.app.modules.browser.extension_risk.service.CrxcavatorProvider.get_versions",
            return_value=[],
        ),
        patch(
            "backend.app.modules.browser.extension_risk.service.CrxcavatorProvider.check_extension",
            return_value={},
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="unknownextid",
        )

    assert outcome.signals == []


@pytest.mark.asyncio
async def test_run_graceful_on_crxcavator_failure() -> None:
    """CRXcavator ProviderError → empty list, no exception raised."""
    service = ExtensionRiskService()
    with (
        patch(
            "backend.app.modules.browser.extension_risk.service.CrxcavatorProvider.get_versions",
            side_effect=ProviderError("CRXcavator down"),
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="someext:1.0.0:Chrome",
        )

    assert outcome.signals == []


@pytest.mark.asyncio
async def test_run_firefox_uses_amo_provider() -> None:
    """Firefox platform uses FirefoxAddonsSiteApiProvider, not ChromeWebStoreApiProvider."""
    service = ExtensionRiskService()
    with (
        patch(
            "backend.app.modules.browser.extension_risk.service.CrxcavatorProvider.check_extension",
            return_value=CRX_REPORT,
        ),
        patch(
            "backend.app.modules.browser.extension_risk.service.FirefoxAddonsSiteApiProvider.get_addon",
            return_value={"guid": "{abc}", "name": "uBlock Origin"},
        ) as mock_amo,
        patch(
            "backend.app.modules.browser.extension_risk.service.ChromeWebStoreApiProvider.get_extension",
        ) as mock_cws,
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="{uBlock0@raymondhill.net}:1.50.0:Firefox",
        )

    mock_amo.assert_called_once()
    mock_cws.assert_not_called()
    assert len(outcome.signals) == 1
    assert outcome.signals[0].evidence["platform"] == "Firefox"


@pytest.mark.asyncio
async def test_run_empty_extension_id_returns_no_signals() -> None:
    service = ExtensionRiskService()
    outcome = await service.run(
        user_id=USER_ID,
        asset_id=ASSET_ID,
        asset_value="",
    )
    assert outcome.signals == []
