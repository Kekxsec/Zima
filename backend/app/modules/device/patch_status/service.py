# backend/app/modules/device/patch_status/service.py
from __future__ import annotations

import platform
import uuid

from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.tools.linux_native.client import LinuxNativeProvider
from backend.app.providers.tools.macos_native.client import MacOsNativeProvider
from backend.app.providers.tools.osquery.client import OsqueryProvider
from backend.app.providers.tools.windows_native.client import WindowsNativeProvider
from backend.app.signals.schemas import SignalCreate

logger = get_logger(__name__)


class PatchStatusService(BaseModuleService):
    """Device patch status assessment.

    Collects OS patch data via osquery (Windows patches table) and platform-
    native providers (macOS auto-update, Windows hotfixes, Linux unattended-
    upgrades). Emits signals when patches are pending or auto-update is off.
    """

    module_name = "patch_status"
    module_domain = "device"
    required_entity_types = [EntityType.DEVICE]

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
        ctx: object = None,
    ) -> list[SignalCreate]:
        signals: list[SignalCreate] = []
        system = platform.system()

        # --- osquery: Windows patches table ---
        if system == "Windows":
            osq = OsqueryProvider()
            try:
                patches = await osq.query_named("patches")
                if patches:
                    signals.append(
                        SignalCreate(
                            signal_type="patch_inventory_collected",
                            category="device_inventory",
                            entity_type=EntityType.DEVICE,
                            entity_id=asset_id,
                            entity_value=asset_value,
                            user_id=user_id,
                            severity=Severity.INFO,
                            confidence=Confidence.HIGH,
                            source=self.module_name,
                            provider="osquery",
                            summary=(
                                f"Windows patch inventory: "
                                f"{len(patches)} hotfixes installed"
                            ),
                            details=f"osquery found {len(patches)} Windows hotfixes.",
                            evidence={
                                "patch_count": len(patches),
                                "patches": patches[:20],
                                "source_provider": "osquery",
                            },
                            tags=["patch_status", "windows", "osquery"],
                            recommended_action=(
                                "Review installed hotfixes and ensure Windows Update "
                                "is configured to install updates automatically."
                            ),
                            source_ref="osquery:patches",
                        )
                    )
            except ProviderError as e:
                logger.warning("patch_status.osquery_unavailable", error=str(e))

        # --- macOS native: auto-update + OS version ---
        if system == "Darwin":
            macos = MacOsNativeProvider()
            try:
                macos_data = await macos.collect()
                auto_update = macos_data.get("auto_update", {})
                if auto_update.get("available") is not False:
                    enabled = auto_update.get("enabled", True)
                    if not enabled:
                        signals.append(
                            SignalCreate(
                                signal_type="auto_update_disabled",
                                category="device_security",
                                entity_type=EntityType.DEVICE,
                                entity_id=asset_id,
                                entity_value=asset_value,
                                user_id=user_id,
                                severity=Severity.MEDIUM,
                                confidence=Confidence.HIGH,
                                source=self.module_name,
                                provider="macos_native",
                                summary="macOS automatic update checks are disabled",
                                details=(
                                    "Automatic macOS software update checks "
                                    "are turned off. Security patches will not "
                                    "be applied automatically."
                                ),
                                evidence={
                                    "auto_update": auto_update,
                                    "source_provider": "macos_native",
                                },
                                tags=["auto_update", "macos", "patch_status"],
                                recommended_action=(
                                    "Enable automatic updates in System Settings > "
                                    "General > Software Update."
                                ),
                                source_ref="macos_native:auto_update",
                            )
                        )
                    else:
                        signals.append(
                            SignalCreate(
                                signal_type="auto_update_enabled",
                                category="device_inventory",
                                entity_type=EntityType.DEVICE,
                                entity_id=asset_id,
                                entity_value=asset_value,
                                user_id=user_id,
                                severity=Severity.INFO,
                                confidence=Confidence.HIGH,
                                source=self.module_name,
                                provider="macos_native",
                                summary="macOS automatic update checks are enabled",
                                details=(
                                    "Automatic macOS software update checks are active."
                                ),
                                evidence={
                                    "auto_update": auto_update,
                                    "source_provider": "macos_native",
                                },
                                tags=["auto_update", "macos", "patch_status"],
                                recommended_action="No action required.",
                                source_ref="macos_native:auto_update",
                            )
                        )
            except ProviderError as e:
                logger.warning("patch_status.macos_native_unavailable", error=str(e))

        # --- Windows native: BitLocker + recent hotfixes ---
        if system == "Windows":
            win = WindowsNativeProvider()
            try:
                win_data = await win.collect()
                hotfixes = win_data.get("hotfixes", [])
                if hotfixes:
                    latest = hotfixes[0] if hotfixes else {}
                    signals.append(
                        SignalCreate(
                            signal_type="patch_inventory_collected",
                            category="device_inventory",
                            entity_type=EntityType.DEVICE,
                            entity_id=asset_id,
                            entity_value=asset_value,
                            user_id=user_id,
                            severity=Severity.INFO,
                            confidence=Confidence.HIGH,
                            source=self.module_name,
                            provider="windows_native",
                            summary=(
                                f"Windows patch inventory: {len(hotfixes)} recent "
                                f"hotfixes, latest {latest.get('HotFixID', '')}"
                            ),
                            details=f"Found {len(hotfixes)} recent Windows hotfixes.",
                            evidence={
                                "hotfix_count": len(hotfixes),
                                "latest_hotfix": latest,
                                "source_provider": "windows_native",
                            },
                            tags=["patch_status", "windows", "hotfix"],
                            recommended_action=(
                                "Ensure Windows Update is set to install updates "
                                "automatically. Review pending security updates."
                            ),
                            source_ref="windows_native:hotfixes",
                        )
                    )
            except ProviderError as e:
                logger.warning("patch_status.windows_native_unavailable", error=str(e))

        # --- Linux native: auto-updates ---
        if system == "Linux":
            lnx = LinuxNativeProvider()
            try:
                lnx_data = await lnx.collect()
                auto_updates = lnx_data.get("auto_updates", {})
                if auto_updates.get("configured") is not False:
                    enabled = auto_updates.get("enabled", False)
                    tool = auto_updates.get("tool", "")
                    if not enabled:
                        signals.append(
                            SignalCreate(
                                signal_type="auto_update_disabled",
                                category="device_security",
                                entity_type=EntityType.DEVICE,
                                entity_id=asset_id,
                                entity_value=asset_value,
                                user_id=user_id,
                                severity=Severity.MEDIUM,
                                confidence=Confidence.MEDIUM,
                                source=self.module_name,
                                provider="linux_native",
                                summary=(
                                    "Linux automatic updates are disabled "
                                    f"({tool or 'unknown tool'})"
                                ),
                                details=(
                                    "Automatic security updates are not enabled. "
                                    "Security patches must be applied manually."
                                ),
                                evidence={
                                    "auto_updates": auto_updates,
                                    "source_provider": "linux_native",
                                },
                                tags=["auto_update", "linux", "patch_status"],
                                recommended_action=(
                                    "Enable unattended-upgrades or equivalent "
                                    "auto-update tooling for your Linux distribution."
                                ),
                                source_ref="linux_native:auto_updates",
                            )
                        )
            except ProviderError as e:
                logger.warning("patch_status.linux_native_unavailable", error=str(e))

        logger.info(
            "patch_status.completed",
            user_id=str(user_id),
            asset_id=str(asset_id),
            signals_emitted=len(signals),
        )
        return signals
