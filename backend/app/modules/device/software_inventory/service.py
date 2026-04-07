# backend/app/modules/device/software_inventory/service.py
import uuid
from typing import Any

from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.tools.syft.client import SyftProvider
from backend.app.signals.schemas import SignalCreate

logger = get_logger(__name__)


def _extract_packages(syft_data: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract normalized package list from Syft JSON output."""
    artifacts = syft_data.get("artifacts", [])
    if not isinstance(artifacts, list):
        return []
    packages: list[dict[str, Any]] = []
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        locations = item.get("locations", [])
        path = locations[0].get("realPath") if locations else None
        packages.append(
            {
                "name": item.get("name"),
                "version": item.get("version"),
                "type": item.get("type"),
                "purl": item.get("purl"),
                "language": item.get("language"),
                "path": path,
            }
        )
    return packages


class SoftwareInventoryService(BaseModuleService):
    module_name = "software_inventory"
    module_domain = "device"
    required_entity_types = [EntityType.DEVICE]

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
        ctx: object = None,
    ) -> list[SignalCreate]:
        """Run Syft against the scan target and emit a coverage signal.

        asset_value: Syft scan target — e.g. "/" for the local filesystem,
                     "dir:/path" for a specific directory, or
                     "docker:image:tag" for a container image.
        """
        signals: list[SignalCreate] = []
        target = asset_value.strip() or "/"

        syft = SyftProvider()
        try:
            syft_data = await syft.scan(target)
        except ProviderError as e:
            logger.error(
                "software_inventory.syft_failure",
                error=str(e),
                target=target,
            )
            return signals

        packages = _extract_packages(syft_data)
        pkg_count = len(packages)

        source_info = syft_data.get("source", {})
        distro_info = syft_data.get("distro", {})
        schema_version = syft_data.get("schema", {}).get("version", "unknown")

        if pkg_count > 0:
            signals.append(
                SignalCreate(
                    signal_type="software_inventory_scan_completed",
                    category="device_inventory",
                    entity_type=EntityType.DEVICE,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=Severity.INFO,
                    confidence=Confidence.HIGH,
                    source=self.module_name,
                    provider="syft",
                    summary=f"Software inventory collected: {pkg_count} packages found",
                    details=(
                        f"Syft v{schema_version} scanned '{target}' and "
                        f"discovered {pkg_count} packages."
                    ),
                    evidence={
                        "packages": packages,
                        "package_count": pkg_count,
                        "scan_target": target,
                        "source": source_info,
                        "distro": distro_info,
                        "syft_schema_version": schema_version,
                    },
                    tags=["software_inventory", "syft", "device_coverage"],
                    recommended_action=(
                        "Review the software inventory for outdated or "
                        "vulnerable packages. Cross-reference against known CVEs."
                    ),
                    source_ref=f"syft:{target}",
                )
            )
        else:
            signals.append(
                SignalCreate(
                    signal_type="software_inventory_scan_empty",
                    category="device_inventory",
                    entity_type=EntityType.DEVICE,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=Severity.INFO,
                    confidence=Confidence.MEDIUM,
                    source=self.module_name,
                    provider="syft",
                    summary="Software inventory scan returned no packages",
                    details=(
                        f"Syft scanned '{target}' but discovered 0 packages. "
                        "Check scan target and permissions."
                    ),
                    evidence={
                        "packages": [],
                        "package_count": 0,
                        "scan_target": target,
                        "source": source_info,
                        "distro": distro_info,
                    },
                    tags=["software_inventory", "syft", "device_coverage", "empty"],
                    recommended_action=(
                        "Verify the scan target is correct and syft has "
                        "sufficient permissions to scan the filesystem."
                    ),
                    source_ref=f"syft:{target}",
                )
            )

        logger.info(
            "software_inventory.completed",
            user_id=str(user_id),
            package_count=pkg_count,
            signals_emitted=len(signals),
        )
        return signals
