# tests/unit/modules/device/test_patch_status.py
import uuid
from unittest.mock import patch

import pytest

from backend.app.core.enums import EntityType, Severity
from backend.app.modules.device.patch_status.service import PatchStatusService
from backend.app.providers.base.exceptions import ProviderError

USER_ID = uuid.uuid4()
ASSET_ID = uuid.uuid4()


@pytest.mark.asyncio
async def test_macos_auto_update_disabled_emits_medium_signal() -> None:
    service = PatchStatusService()
    macos_data = {
        "auto_update": {"available": True, "enabled": False},
    }
    with (
        patch(
            "backend.app.modules.device.patch_status.service.platform.system",
            return_value="Darwin",
        ),
        patch(
            "backend.app.modules.device.patch_status.service.MacOsNativeProvider.collect",
            return_value=macos_data,
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    assert len(outcome.signals) == 1
    s = outcome.signals[0]
    assert s.signal_type == "auto_update_disabled"
    assert s.severity == Severity.MEDIUM
    assert s.provider == "macos_native"
    assert s.entity_type == EntityType.DEVICE


@pytest.mark.asyncio
async def test_macos_auto_update_enabled_emits_info_signal() -> None:
    service = PatchStatusService()
    macos_data = {
        "auto_update": {"available": True, "enabled": True},
    }
    with (
        patch(
            "backend.app.modules.device.patch_status.service.platform.system",
            return_value="Darwin",
        ),
        patch(
            "backend.app.modules.device.patch_status.service.MacOsNativeProvider.collect",
            return_value=macos_data,
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    assert len(outcome.signals) == 1
    s = outcome.signals[0]
    assert s.signal_type == "auto_update_enabled"
    assert s.severity == Severity.INFO


@pytest.mark.asyncio
async def test_macos_provider_failure_returns_empty() -> None:
    service = PatchStatusService()
    with (
        patch(
            "backend.app.modules.device.patch_status.service.platform.system",
            return_value="Darwin",
        ),
        patch(
            "backend.app.modules.device.patch_status.service.MacOsNativeProvider.collect",
            side_effect=ProviderError("macos_native unavailable"),
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    assert outcome.signals == []


@pytest.mark.asyncio
async def test_linux_auto_update_disabled_emits_medium_signal() -> None:
    service = PatchStatusService()
    lnx_data = {
        "auto_updates": {
            "configured": True,
            "enabled": False,
            "tool": "unattended-upgrades",
        },
    }
    with (
        patch(
            "backend.app.modules.device.patch_status.service.platform.system",
            return_value="Linux",
        ),
        patch(
            "backend.app.modules.device.patch_status.service.LinuxNativeProvider.collect",
            return_value=lnx_data,
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    assert len(outcome.signals) == 1
    s = outcome.signals[0]
    assert s.signal_type == "auto_update_disabled"
    assert s.severity == Severity.MEDIUM
    assert s.provider == "linux_native"
    assert "unattended-upgrades" in s.summary


@pytest.mark.asyncio
async def test_windows_osquery_patches_emits_info_signal() -> None:
    service = PatchStatusService()
    patches = [{"HotFixID": "KB5000000"}, {"HotFixID": "KB5000001"}]
    win_data: dict = {"hotfixes": []}
    with (
        patch(
            "backend.app.modules.device.patch_status.service.platform.system",
            return_value="Windows",
        ),
        patch(
            "backend.app.modules.device.patch_status.service.OsqueryProvider.query_named",
            return_value=patches,
        ),
        patch(
            "backend.app.modules.device.patch_status.service.WindowsNativeProvider.collect",
            return_value=win_data,
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    inv_signals = [
        s for s in outcome.signals if s.signal_type == "patch_inventory_collected"
    ]
    assert len(inv_signals) >= 1
    assert inv_signals[0].provider == "osquery"
    assert inv_signals[0].evidence["patch_count"] == 2
