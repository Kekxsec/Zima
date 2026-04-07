# tests/unit/modules/device/test_software_inventory.py
import uuid
from unittest.mock import patch

import pytest

from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.modules.device.software_inventory.service import (
    SoftwareInventoryService,
    _extract_packages,
)
from backend.app.providers.base.exceptions import ProviderError

USER_ID = uuid.uuid4()
ASSET_ID = uuid.uuid4()

SAMPLE_SYFT_OUTPUT = {
    "schema": {"version": "16.0.0"},
    "source": {"type": "directory", "target": "/"},
    "distro": {"name": "Ubuntu", "version": "22.04"},
    "artifacts": [
        {
            "name": "bash",
            "version": "5.1.16",
            "type": "deb",
            "purl": "pkg:deb/ubuntu/bash@5.1.16",
            "language": "",
            "locations": [{"realPath": "/usr/bin/bash"}],
        },
        {
            "name": "python3",
            "version": "3.11.2",
            "type": "deb",
            "purl": "pkg:deb/ubuntu/python3@3.11.2",
            "language": "python",
            "locations": [{"realPath": "/usr/bin/python3"}],
        },
    ],
}

EMPTY_SYFT_OUTPUT = {
    "schema": {"version": "16.0.0"},
    "source": {"type": "directory", "target": "/tmp/empty"},  # noqa: S108
    "distro": {},
    "artifacts": [],
}


# ─── Helper ───────────────────────────────────────────────────────────────────


def test_extract_packages_returns_normalized_list() -> None:
    packages = _extract_packages(SAMPLE_SYFT_OUTPUT)
    assert len(packages) == 2
    assert packages[0]["name"] == "bash"
    assert packages[0]["version"] == "5.1.16"
    assert packages[0]["purl"] == "pkg:deb/ubuntu/bash@5.1.16"
    assert packages[0]["path"] == "/usr/bin/bash"
    assert packages[1]["language"] == "python"


def test_extract_packages_handles_missing_locations() -> None:
    data = {
        "artifacts": [
            {
                "name": "pkg",
                "version": "1.0",
                "type": "deb",
                "purl": "pkg:deb/pkg@1.0",
                "language": "",
                "locations": [],
            }
        ]
    }
    packages = _extract_packages(data)
    assert packages[0]["path"] is None


def test_extract_packages_returns_empty_on_bad_input() -> None:
    assert _extract_packages({}) == []
    assert _extract_packages({"artifacts": "not-a-list"}) == []


# ─── Service ──────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_emits_completed_signal_with_packages() -> None:
    service = SoftwareInventoryService()
    with patch(
        "backend.app.modules.device.software_inventory.service.SyftProvider.scan",
        return_value=SAMPLE_SYFT_OUTPUT,
    ):
        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="/",
        )

    assert len(signals) == 1
    s = signals[0]
    assert s.signal_type == "software_inventory_scan_completed"
    assert s.severity == Severity.INFO
    assert s.confidence == Confidence.HIGH
    assert s.entity_type == EntityType.DEVICE
    assert s.provider == "syft"
    assert s.evidence["package_count"] == 2
    assert len(s.evidence["packages"]) == 2
    assert s.evidence["scan_target"] == "/"


@pytest.mark.asyncio
async def test_run_emits_empty_signal_when_no_packages_found() -> None:
    service = SoftwareInventoryService()
    with patch(
        "backend.app.modules.device.software_inventory.service.SyftProvider.scan",
        return_value=EMPTY_SYFT_OUTPUT,
    ):
        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="/tmp/empty",  # noqa: S108
        )

    assert len(signals) == 1
    s = signals[0]
    assert s.signal_type == "software_inventory_scan_empty"
    assert s.severity == Severity.INFO
    assert s.confidence == Confidence.MEDIUM
    assert s.evidence["package_count"] == 0


@pytest.mark.asyncio
async def test_run_graceful_on_syft_failure() -> None:
    """Syft ProviderError must not propagate — returns empty list."""
    service = SoftwareInventoryService()
    with patch(
        "backend.app.modules.device.software_inventory.service.SyftProvider.scan",
        side_effect=ProviderError("syft binary not found"),
    ):
        signals = await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="/",
        )

    assert signals == []


@pytest.mark.asyncio
async def test_run_defaults_target_to_root_when_asset_value_empty() -> None:
    service = SoftwareInventoryService()
    with patch(
        "backend.app.modules.device.software_inventory.service.SyftProvider.scan",
        return_value=SAMPLE_SYFT_OUTPUT,
    ) as mock_scan:
        await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="",
        )

    mock_scan.assert_called_once_with("/")


@pytest.mark.asyncio
async def test_run_passes_custom_target() -> None:
    service = SoftwareInventoryService()
    with patch(
        "backend.app.modules.device.software_inventory.service.SyftProvider.scan",
        return_value=SAMPLE_SYFT_OUTPUT,
    ) as mock_scan:
        await service.run(
            user_id=USER_ID,
            asset_id=ASSET_ID,
            asset_value="docker:nginx:latest",
        )

    mock_scan.assert_called_once_with("docker:nginx:latest")
