# tests/unit/modules/device/test_device_inventory.py
import uuid
from unittest.mock import patch

import pytest

from backend.app.core.enums import EntityType, Severity
from backend.app.modules.device.device_inventory.service import DeviceInventoryService
from backend.app.providers.base.exceptions import ProviderError

USER_ID = uuid.uuid4()
ASSET_ID = uuid.uuid4()


def _iface(
    name: str = "en0",
    mac: str = "aa:bb:cc:dd:ee:ff",
    ip: str = "192.168.1.10",
) -> dict:  # type: ignore[type-arg]
    return {
        "interface": name,
        "mac": mac,
        "address": ip,
        "type": "6",
        "flags": "4163",
    }


@pytest.mark.asyncio
async def test_network_interface_signal_emitted_per_interface() -> None:
    service = DeviceInventoryService()
    with (
        patch(
            "backend.app.modules.device.device_inventory.service.OsqueryProvider.query_named",
            return_value=[
                _iface("en0"),
                _iface("en1", "11:22:33:44:55:66", "10.0.0.2"),
            ],
        ),
        patch(
            "backend.app.modules.device.device_inventory.service.OuiMasterDatabaseProvider.lookup_many",
            return_value=[
                {"mac": "aa:bb:cc:dd:ee:ff", "vendor": "Apple Inc."},
                {"mac": "11:22:33:44:55:66", "vendor": "Intel Corp."},
            ],
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    assert len(outcome.signals) == 2
    s = outcome.signals[0]
    assert s.signal_type == "network_interface_discovered"
    assert s.severity == Severity.INFO
    assert s.entity_type == EntityType.DEVICE
    assert s.provider == "osquery+oui_master_database"


@pytest.mark.asyncio
async def test_vendor_enrichment_appears_in_summary() -> None:
    service = DeviceInventoryService()
    with (
        patch(
            "backend.app.modules.device.device_inventory.service.OsqueryProvider.query_named",
            return_value=[_iface("en0", "aa:bb:cc:dd:ee:ff")],
        ),
        patch(
            "backend.app.modules.device.device_inventory.service.OuiMasterDatabaseProvider.lookup_many",
            return_value=[{"mac": "aa:bb:cc:dd:ee:ff", "vendor": "Apple Inc."}],
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    assert len(outcome.signals) == 1
    s = outcome.signals[0]
    assert "Apple Inc." in s.summary
    assert s.evidence["vendor"] == "Apple Inc."


@pytest.mark.asyncio
async def test_loopback_interface_skipped() -> None:
    """Interfaces with MAC 00:00:00:00:00:00 or empty MAC are not emitted."""
    service = DeviceInventoryService()
    with (
        patch(
            "backend.app.modules.device.device_inventory.service.OsqueryProvider.query_named",
            return_value=[
                _iface("lo0", mac="00:00:00:00:00:00"),
                _iface("en0", mac="aa:bb:cc:dd:ee:ff"),
            ],
        ),
        patch(
            "backend.app.modules.device.device_inventory.service.OuiMasterDatabaseProvider.lookup_many",
            return_value=[{"mac": "aa:bb:cc:dd:ee:ff", "vendor": "Apple Inc."}],
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    # Only en0 should emit — lo0 filtered out
    assert len(outcome.signals) == 1
    assert "en0" in outcome.signals[0].summary


@pytest.mark.asyncio
async def test_osquery_failure_returns_empty() -> None:
    service = DeviceInventoryService()
    with patch(
        "backend.app.modules.device.device_inventory.service.OsqueryProvider.query_named",
        side_effect=ProviderError("osquery unavailable"),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    assert outcome.signals == []


@pytest.mark.asyncio
async def test_no_interfaces_returns_empty() -> None:
    service = DeviceInventoryService()
    with (
        patch(
            "backend.app.modules.device.device_inventory.service.OsqueryProvider.query_named",
            return_value=[],
        ),
        patch(
            "backend.app.modules.device.device_inventory.service.OuiMasterDatabaseProvider.lookup_many",
            return_value=[],
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    assert outcome.signals == []


@pytest.mark.asyncio
async def test_oui_lookup_failure_still_emits_signals() -> None:
    """OUI lookup failure → vendor is empty string but signals still emitted."""
    service = DeviceInventoryService()
    with (
        patch(
            "backend.app.modules.device.device_inventory.service.OsqueryProvider.query_named",
            return_value=[_iface("en0", "aa:bb:cc:dd:ee:ff")],
        ),
        patch(
            "backend.app.modules.device.device_inventory.service.OuiMasterDatabaseProvider.lookup_many",
            side_effect=Exception("OUI database missing"),
        ),
    ):
        outcome = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="device-001",
        )

    assert len(outcome.signals) == 1
    assert outcome.signals[0].evidence["vendor"] == ""
