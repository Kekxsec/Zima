# tests/integration/test_e2e_pillars.py
"""
End-to-end scan tests for the identity, device, and browser pillars.

Each test instantiates the relevant module service, mocks all outbound
provider calls, and verifies that the service produces the expected signals.
These tests exercise the full service path — rule evaluation, signal
construction, severity mapping — without touching the database or real APIs.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.core.enums import EntityType, Severity
from backend.app.modules.browser.extension_risk.service import ExtensionRiskService
from backend.app.modules.device.os_security.service import OsSecurityService
from backend.app.modules.identity.breach_monitor.service import BreachMonitorService
from backend.app.modules.identity.credential_exposure.service import (
    CredentialExposureService,
)
from backend.app.modules.identity.stealer_log_exposure.service import (
    StealerLogExposureService,
)
from backend.app.providers.base.models import ProviderResult

USER_ID = uuid.uuid4()
ASSET_ID = uuid.uuid4()

# ---------------------------------------------------------------------------
# Shared provider-result helpers
# ---------------------------------------------------------------------------


def _ok(provider: str, findings: list[dict]) -> ProviderResult:
    return ProviderResult(provider=provider, success=True, findings=findings)


def _skipped(provider: str) -> ProviderResult:
    return ProviderResult(
        provider=provider,
        success=False,
        findings=[],
        reason="missing_credentials",
        skipped=True,
    )


# ---------------------------------------------------------------------------
# Identity pillar — breach_monitor
# ---------------------------------------------------------------------------

_HIBP_FINDING = {
    "title": "Adobe",
    "description": "Adobe breach 2013",
    "tags": ["breach"],
    "raw": {"breach_name": "adobe", "pwn_count": 153000000},
}

_DEHASHED_FINDING = {
    "title": "dehashed_unknown",
    "description": "DeHashed result",
    "tags": [],
    "raw": {"total": 3, "entries": [{"password": "hunter2"}]},
}


@pytest.mark.asyncio
async def test_identity_pillar_breach_monitor_emits_signals() -> None:
    """BreachMonitorService: HIBP + DeHashed hits → signals with correct severity."""
    service = BreachMonitorService()

    hibp_result = _ok("haveibeenpwned", [_HIBP_FINDING])
    dh_result = _ok("dehashed", [_DEHASHED_FINDING])
    bd_result = _skipped("breachdirectory")

    with patch(
        "backend.app.modules.identity.breach_monitor.service.run_provider",
        side_effect=[hibp_result, dh_result, bd_result],
    ):
        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="victim@example.com",
        )

    assert len(signals) == 2

    hibp_sig = next(s for s in signals if s.provider == "haveibeenpwned")
    assert hibp_sig.signal_type == "email_breached"
    assert hibp_sig.entity_type == EntityType.EMAIL
    assert hibp_sig.severity == Severity.HIGH

    dh_sig = next(s for s in signals if s.provider == "dehashed")
    # plaintext password in entry → CRITICAL
    assert dh_sig.severity == Severity.CRITICAL


@pytest.mark.asyncio
async def test_identity_pillar_breach_monitor_all_skipped_returns_empty() -> None:
    """All providers skipped (no credentials) → no signals emitted."""
    service = BreachMonitorService()

    with patch(
        "backend.app.modules.identity.breach_monitor.service.run_provider",
        side_effect=[
            _skipped("haveibeenpwned"),
            _skipped("dehashed"),
            _skipped("breachdirectory"),
        ],
    ):
        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="nobody@example.com",
        )

    assert signals == []


# ---------------------------------------------------------------------------
# Identity pillar — credential_exposure
# ---------------------------------------------------------------------------

_LEAKCHECK_FINDING = {
    "title": "credential_exposure:nobody@example.com",
    "description": "LeakCheck: 2 sources",
    "tags": ["credential_exposure"],
    "raw": {
        "has_password": True,
        "breach_name": "SomeBreach",
        "breach_date": "2023-01-01",
    },
}


@pytest.mark.asyncio
async def test_identity_pillar_credential_exposure_emits_signal() -> None:
    """CredentialExposureService: LeakCheck hit with has_password → signal emitted."""
    service = CredentialExposureService()

    # Three providers are called in sequence: dehashed, leakcheck, breachdirectory.
    # Only the leakcheck result carries a qualifying finding.
    with patch(
        "backend.app.modules.identity.credential_exposure.service.run_provider",
        side_effect=[
            _skipped("dehashed"),
            _ok("leakcheck", [_LEAKCHECK_FINDING]),
            _skipped("breachdirectory"),
        ],
    ):
        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="nobody@example.com",
        )

    assert len(signals) >= 1
    sig = signals[0]
    assert sig.signal_type == "password_exposed"
    assert sig.entity_type == EntityType.EMAIL
    assert sig.provider == "leakcheck"


# ---------------------------------------------------------------------------
# Identity pillar — stealer_log_exposure
# ---------------------------------------------------------------------------

_STEALER_FINDING = {
    "provider": "hudson_rock",
    "category": "stealer_log_exposure",
    "title": "Stealer log hit: victim@example.com",
    "description": "RedLine infostealer. 42 credentials.",
    "entity_type": "email",
    "entity_value": "victim@example.com",
    "tags": ["stealer_log"],
    "raw": {
        "date_uploaded": "2024-01-15",
        "operating_system": "Windows 10",
        "malware_name": "RedLine",
        "credential_count": 42,
    },
}


@pytest.mark.asyncio
async def test_identity_pillar_stealer_log_exposure_emits_critical_signal() -> None:
    """StealerLogExposureService: Hudson Rock hit → CRITICAL stealer_log signal."""
    service = StealerLogExposureService()

    with patch(
        "backend.app.modules.identity.stealer_log_exposure.service.run_provider",
        return_value=_ok("hudson_rock", [_STEALER_FINDING]),
    ):
        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="victim@example.com",
        )

    assert len(signals) >= 1
    assert signals[0].severity == Severity.CRITICAL
    assert signals[0].signal_type == "stealer_log_hit"


# ---------------------------------------------------------------------------
# Device pillar — os_security
# ---------------------------------------------------------------------------

_LYNIS_OUTPUT = {
    "hardening_index": 45,
    "warnings": [
        {"test_id": "KRNL-5820", "description": "Kernel update available"},
        {"test_id": "AUTH-9328", "description": "Root has no password"},
        {"test_id": "FIRE-4512", "description": "Firewall not active"},
        {"test_id": "MAIL-8804", "description": "MTA scan results"},
        {"test_id": "INSE-8016", "description": "Insecure service active"},
    ],
    "suggestions": [],
    "tests_done": 120,
    "tests_skipped": 5,
}

_OSQUERY_OS_ROW = {"name": "Ubuntu", "version": "22.04", "platform": "ubuntu"}
_OSQUERY_KERNEL_ROW = {"version": "5.15.0", "description": "Linux"}


@pytest.mark.asyncio
async def test_device_pillar_os_security_emits_signal_on_weak_hardening() -> None:
    """OsSecurityService: low hardening index + warnings → HIGH os_hardening signal."""
    from backend.app.providers.base.exceptions import ProviderError

    service = OsSecurityService()

    with (
        patch(
            "backend.app.modules.device.os_security.service.OsqueryProvider.query_named",
            new_callable=AsyncMock,
            side_effect=[[_OSQUERY_OS_ROW], [_OSQUERY_KERNEL_ROW]],
        ),
        patch(
            "backend.app.modules.device.os_security.service.MacOsNativeProvider.collect",
            new_callable=AsyncMock,
            side_effect=ProviderError("macos_native unavailable"),
        ),
        patch(
            "backend.app.modules.device.os_security.service.LynisProvider.audit",
            new_callable=AsyncMock,
            return_value=_LYNIS_OUTPUT,
        ),
    ):
        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    assert len(signals) >= 1
    lynis_sigs = [s for s in signals if s.provider == "lynis"]
    assert len(lynis_sigs) >= 1
    assert lynis_sigs[0].severity == Severity.HIGH


@pytest.mark.asyncio
async def test_device_pillar_os_security_graceful_on_lynis_failure() -> None:
    """OsSecurityService: lynis ProviderError → degrades gracefully, no exception."""
    from backend.app.providers.base.exceptions import ProviderError

    service = OsSecurityService()

    with (
        patch(
            "backend.app.modules.device.os_security.service.OsqueryProvider.query_named",
            new_callable=AsyncMock,
            side_effect=[[_OSQUERY_OS_ROW], [_OSQUERY_KERNEL_ROW]],
        ),
        patch(
            "backend.app.modules.device.os_security.service.MacOsNativeProvider.collect",
            new_callable=AsyncMock,
            side_effect=ProviderError("macos_native unavailable"),
        ),
        patch(
            "backend.app.modules.device.os_security.service.LynisProvider.audit",
            new_callable=AsyncMock,
            side_effect=ProviderError("lynis unavailable"),
        ),
    ):
        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    # May emit osquery-derived signals even if lynis fails — just no crash
    assert isinstance(signals, list)


# ---------------------------------------------------------------------------
# Browser pillar — extension_risk (CRXcavator path)
# ---------------------------------------------------------------------------

_CRX_REPORT_HIGH = {
    "data": {
        "risk": {
            "total": 550,
            "csp": {"total": 150},
            "permissions": {"total": 220},
            "retire": {"total": 100},
            "webstore": {"total": 80},
        }
    }
}


@pytest.mark.asyncio
async def test_browser_pillar_extension_risk_crx_path_emits_signal() -> None:
    """ExtensionRiskService (CRXcavator path): high-risk extension → HIGH signal."""
    service = ExtensionRiskService()

    with (
        patch(
            "backend.app.modules.browser.extension_risk.service.CrxcavatorProvider.check_extension",
            new_callable=AsyncMock,
            return_value=_CRX_REPORT_HIGH,
        ),
        patch(
            "backend.app.modules.browser.extension_risk.service.ChromeWebStoreApiProvider.get_extension",
            new_callable=AsyncMock,
            return_value={"id": "cfhdojbkjhnklbpkdaibdccddilifddb", "name": "SomeExt"},
        ),
    ):
        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="cfhdojbkjhnklbpkdaibdccddilifddb:2.0.0:Chrome",
        )

    assert len(signals) == 1
    sig = signals[0]
    assert sig.signal_type == "browser_extension_risk"
    assert sig.severity == Severity.HIGH
    assert sig.provider == "crxcavator"
    assert sig.evidence["extension_id"] == "cfhdojbkjhnklbpkdaibdccddilifddb"
    assert sig.evidence["store_metadata"]["name"] == "SomeExt"


@pytest.mark.asyncio
async def test_browser_pillar_extension_risk_firefox_uses_amo() -> None:
    """ExtensionRiskService (Firefox): AMO enrichment is used, CWS is not called."""
    service = ExtensionRiskService()

    with (
        patch(
            "backend.app.modules.browser.extension_risk.service.CrxcavatorProvider.check_extension",
            new_callable=AsyncMock,
            return_value=_CRX_REPORT_HIGH,
        ),
        patch(
            "backend.app.modules.browser.extension_risk.service.FirefoxAddonsSiteApiProvider.get_addon",
            new_callable=AsyncMock,
            return_value={"guid": "{uBlock0@raymondhill.net}", "name": "uBlock Origin"},
        ) as mock_amo,
        patch(
            "backend.app.modules.browser.extension_risk.service.ChromeWebStoreApiProvider.get_extension",
            new_callable=AsyncMock,
        ) as mock_cws,
    ):
        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="{uBlock0@raymondhill.net}:1.50.0:Firefox",
        )

    mock_amo.assert_called_once()
    mock_cws.assert_not_called()
    assert len(signals) == 1
    assert signals[0].evidence["platform"] == "Firefox"


@pytest.mark.asyncio
async def test_browser_pillar_extension_risk_device_path_no_extensions() -> None:
    """ExtensionRiskService (device path): no installed extensions → empty list."""
    service = ExtensionRiskService()

    with patch(
        "backend.app.modules.browser.extension_risk.service.BrowserExtensionDetectorProvider.scan",
        new_callable=AsyncMock,
        return_value=[],
    ):
        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="macbook-pro-2023",
        )

    assert signals == []


@pytest.mark.asyncio
async def test_browser_pillar_extension_risk_device_path_malicious_hit() -> None:
    """ExtensionRiskService (device path): malicious extension detected → CRITICAL."""
    service = ExtensionRiskService()

    installed = [
        {
            "extension_id": "abcdefghijklmnopabcdefghijklmnop",
            "name": "FakeAdblock",
            "version": "1.0.0",
            "browser": "chrome",
            "profile": "Default",
        }
    ]
    malicious_hit = [
        {
            "extension_id": "abcdefghijklmnopabcdefghijklmnop",
            "name": "FakeAdblock",
            "date_added": "2024-06-01",
            "source_url": "https://example.com/report",
        }
    ]

    with (
        patch(
            "backend.app.modules.browser.extension_risk.service.BrowserExtensionDetectorProvider.scan",
            new_callable=AsyncMock,
            return_value=installed,
        ),
        patch(
            "backend.app.modules.browser.extension_risk.service.MaliciousExtensionSentryProvider.check_extensions",
            new_callable=AsyncMock,
            return_value=malicious_hit,
        ),
    ):
        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="macbook-pro-2023",
        )

    assert len(signals) == 1
    assert signals[0].signal_type == "malicious_extension_found"
    assert signals[0].severity == Severity.CRITICAL
    assert signals[0].entity_type == EntityType.DEVICE
