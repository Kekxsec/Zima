# tests/unit/modules/device/test_os_security.py
import uuid
from unittest.mock import patch

import pytest

from backend.app.core.enums import EntityType, Severity
from backend.app.modules.device.os_security.service import OsSecurityService
from backend.app.providers.base.exceptions import ProviderError

USER_ID = uuid.uuid4()
ASSET_ID = uuid.uuid4()

_OS_ROWS = [{"name": "macOS", "version": "14.0", "build": "23A344"}]
_KERNEL_ROWS = [{"version": "22.6.0", "arguments": ""}]
_MACOS_CLEAN = {
    "sip": {"available": True, "enabled": True},
    "filevault": {"available": True, "enabled": True},
    "gatekeeper": {"available": True, "enabled": True},
    "auto_update": {"available": True, "enabled": True},
}


@pytest.mark.asyncio
async def test_os_version_signal_emitted_from_osquery() -> None:
    service = OsSecurityService()
    with (
        patch(
            "backend.app.modules.device.os_security.service.OsqueryProvider.query_named",
            side_effect=[_OS_ROWS, _KERNEL_ROWS],
        ),
        patch(
            "backend.app.modules.device.os_security.service.MacOsNativeProvider.collect",
            return_value={},
        ),
        patch(
            "backend.app.modules.device.os_security.service.LynisProvider.audit",
            side_effect=ProviderError("lynis not found"),
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    assert len(outcome.signals) == 1
    s = outcome.signals[0]
    assert s.signal_type == "os_version_collected"
    assert s.severity == Severity.INFO
    assert s.entity_type == EntityType.DEVICE
    assert s.provider == "osquery"
    assert "macOS" in s.summary


@pytest.mark.asyncio
async def test_sip_disabled_emits_high_signal() -> None:
    service = OsSecurityService()
    macos_data = {
        **_MACOS_CLEAN,
        "sip": {"available": True, "enabled": False},
    }
    with (
        patch(
            "backend.app.modules.device.os_security.service.OsqueryProvider.query_named",
            side_effect=[[], []],
        ),
        patch(
            "backend.app.modules.device.os_security.service.MacOsNativeProvider.collect",
            return_value=macos_data,
        ),
        patch(
            "backend.app.modules.device.os_security.service.LynisProvider.audit",
            side_effect=ProviderError("lynis not found"),
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    sip_signals = [s for s in outcome.signals if s.signal_type == "sip_disabled"]
    assert len(sip_signals) == 1
    assert sip_signals[0].severity == Severity.HIGH
    assert sip_signals[0].provider == "macos_native"


@pytest.mark.asyncio
async def test_filevault_disabled_emits_high_signal() -> None:
    service = OsSecurityService()
    macos_data = {
        **_MACOS_CLEAN,
        "filevault": {"available": True, "enabled": False},
    }
    with (
        patch(
            "backend.app.modules.device.os_security.service.OsqueryProvider.query_named",
            side_effect=[[], []],
        ),
        patch(
            "backend.app.modules.device.os_security.service.MacOsNativeProvider.collect",
            return_value=macos_data,
        ),
        patch(
            "backend.app.modules.device.os_security.service.LynisProvider.audit",
            side_effect=ProviderError("lynis not found"),
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    fv_signals = [
        s for s in outcome.signals if s.signal_type == "disk_encryption_disabled"
    ]
    assert len(fv_signals) == 1
    assert fv_signals[0].severity == Severity.HIGH


@pytest.mark.asyncio
async def test_gatekeeper_disabled_emits_medium_signal() -> None:
    service = OsSecurityService()
    macos_data = {
        **_MACOS_CLEAN,
        "gatekeeper": {"available": True, "enabled": False},
    }
    with (
        patch(
            "backend.app.modules.device.os_security.service.OsqueryProvider.query_named",
            side_effect=[[], []],
        ),
        patch(
            "backend.app.modules.device.os_security.service.MacOsNativeProvider.collect",
            return_value=macos_data,
        ),
        patch(
            "backend.app.modules.device.os_security.service.LynisProvider.audit",
            side_effect=ProviderError("lynis not found"),
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    gk_signals = [s for s in outcome.signals if s.signal_type == "gatekeeper_disabled"]
    assert len(gk_signals) == 1
    assert gk_signals[0].severity == Severity.MEDIUM


@pytest.mark.asyncio
async def test_lynis_low_hardening_index_emits_high_signal() -> None:
    """Hardening index below 50 → HIGH severity."""
    service = OsSecurityService()
    with (
        patch(
            "backend.app.modules.device.os_security.service.OsqueryProvider.query_named",
            side_effect=[[], []],
        ),
        patch(
            "backend.app.modules.device.os_security.service.MacOsNativeProvider.collect",
            return_value={},
        ),
        patch(
            "backend.app.modules.device.os_security.service.LynisProvider.audit",
            return_value={"hardening_index": 40, "warnings": [], "suggestions": []},
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    lynis_signals = [
        s for s in outcome.signals if s.signal_type == "os_hardening_assessed"
    ]
    assert len(lynis_signals) == 1
    assert lynis_signals[0].severity == Severity.HIGH
    assert lynis_signals[0].evidence["hardening_index"] == 40


@pytest.mark.asyncio
async def test_lynis_medium_hardening_index_emits_medium_signal() -> None:
    """Hardening index 50–69 → MEDIUM severity."""
    service = OsSecurityService()
    with (
        patch(
            "backend.app.modules.device.os_security.service.OsqueryProvider.query_named",
            side_effect=[[], []],
        ),
        patch(
            "backend.app.modules.device.os_security.service.MacOsNativeProvider.collect",
            return_value={},
        ),
        patch(
            "backend.app.modules.device.os_security.service.LynisProvider.audit",
            return_value={"hardening_index": 60, "warnings": [], "suggestions": []},
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    lynis_signals = [
        s for s in outcome.signals if s.signal_type == "os_hardening_assessed"
    ]
    assert len(lynis_signals) == 1
    assert lynis_signals[0].severity == Severity.MEDIUM


@pytest.mark.asyncio
async def test_lynis_high_hardening_index_emits_low_signal() -> None:
    """Hardening index ≥ 70 with no warnings → LOW severity."""
    service = OsSecurityService()
    with (
        patch(
            "backend.app.modules.device.os_security.service.OsqueryProvider.query_named",
            side_effect=[[], []],
        ),
        patch(
            "backend.app.modules.device.os_security.service.MacOsNativeProvider.collect",
            return_value={},
        ),
        patch(
            "backend.app.modules.device.os_security.service.LynisProvider.audit",
            return_value={
                "hardening_index": 80,
                "warnings": [],
                "suggestions": ["Consider enabling audit logging"],
            },
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    lynis_signals = [
        s for s in outcome.signals if s.signal_type == "os_hardening_assessed"
    ]
    assert len(lynis_signals) == 1
    assert lynis_signals[0].severity == Severity.LOW


@pytest.mark.asyncio
async def test_osquery_failure_does_not_stop_other_checks() -> None:
    """osquery failure → skip OS signal but continue to lynis."""
    service = OsSecurityService()
    with (
        patch(
            "backend.app.modules.device.os_security.service.OsqueryProvider.query_named",
            side_effect=ProviderError("osquery not installed"),
        ),
        patch(
            "backend.app.modules.device.os_security.service.MacOsNativeProvider.collect",
            return_value={},
        ),
        patch(
            "backend.app.modules.device.os_security.service.LynisProvider.audit",
            return_value={"hardening_index": 55, "warnings": [], "suggestions": []},
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    # lynis should still emit a signal
    assert any(s.signal_type == "os_hardening_assessed" for s in outcome.signals)
