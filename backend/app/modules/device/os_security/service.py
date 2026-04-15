# backend/app/modules/device/os_security/service.py
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.outcome import ModuleOutcome
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.tools.lynis.client import LynisProvider
from backend.app.providers.tools.macos_native.client import MacOsNativeProvider
from backend.app.providers.tools.osquery.client import OsqueryProvider
from backend.app.signals.schemas import SignalCreate

if TYPE_CHECKING:
    from backend.app.jobs.context import ScanExecutionContext

logger = get_logger(__name__)

# Lynis hardening index thresholds
_HARDENING_LOW = 50
_HARDENING_MEDIUM = 70

# Lynis warnings that indicate HIGH-severity OS issues
_HIGH_SEVERITY_WARNINGS = frozenset(
    [
        "KRNL-5820",  # kernel update available
        "AUTH-9328",  # password not set for root
        "BOOT-5122",  # bootloader config not protected
    ]
)


def _lynis_severity(hardening_index: int, warning_count: int) -> Severity:
    if hardening_index < _HARDENING_LOW or warning_count >= 5:
        return Severity.HIGH
    if hardening_index < _HARDENING_MEDIUM or warning_count >= 2:
        return Severity.MEDIUM
    return Severity.LOW


class OsSecurityService(BaseModuleService):
    """OS security assessment using osquery telemetry and lynis audit.

    Runs against DEVICE assets. Collects OS version + kernel info via osquery,
    then runs a lynis audit to assess the hardening posture.
    """

    module_name = "os_security"
    module_domain = "device"
    required_entity_types = [EntityType.DEVICE]

    async def run(
        self,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        asset_value: str,
        ctx: ScanExecutionContext | None = None,
    ) -> ModuleOutcome:
        signals: list[SignalCreate] = []

        # --- osquery: OS version + kernel ---
        osq = OsqueryProvider()
        os_rows: list[dict[str, Any]] = []
        kernel_rows: list[dict[str, Any]] = []
        try:
            os_rows = await osq.query_named("os_version")
            kernel_rows = await osq.query_named("kernel_info")
        except ProviderError as e:
            logger.warning("os_security.osquery_unavailable", error=str(e))

        os_info = os_rows[0] if os_rows else {}
        kernel_info = kernel_rows[0] if kernel_rows else {}

        os_name = os_info.get("name", "")
        os_version = os_info.get("version", "")
        kernel_version = kernel_info.get("version", "")

        if os_info:
            signals.append(
                SignalCreate(
                    signal_type="os_version_collected",
                    category="device_inventory",
                    entity_type=EntityType.DEVICE,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=Severity.INFO,
                    confidence=Confidence.HIGH,
                    source=self.module_name,
                    provider="osquery",
                    summary=f"OS identified: {os_name} {os_version}",
                    details=f"Kernel: {kernel_version}",
                    evidence={
                        "os": os_info,
                        "kernel": kernel_info,
                        "source_provider": "osquery",
                    },
                    tags=["os_version", "osquery", "device_coverage"],
                    recommended_action=(
                        "Ensure the operating system and kernel are on a supported "
                        "version with current security patches applied."
                    ),
                    source_ref=f"osquery:os_version:{os_name}",
                )
            )

        # --- macOS-native: SIP, FileVault, Gatekeeper, auto-update ---
        macos = MacOsNativeProvider()
        macos_data: dict[str, Any] = {}
        try:
            macos_data = await macos.collect()
        except ProviderError as e:
            logger.debug("os_security.macos_native_unavailable", error=str(e))

        if macos_data:
            sip = macos_data.get("sip", {})
            filevault = macos_data.get("filevault", {})
            gatekeeper = macos_data.get("gatekeeper", {})

            if sip.get("available") is not False and not sip.get("enabled", True):
                signals.append(
                    SignalCreate(
                        signal_type="sip_disabled",
                        category="device_security",
                        entity_type=EntityType.DEVICE,
                        entity_id=asset_id,
                        entity_value=asset_value,
                        user_id=user_id,
                        severity=Severity.HIGH,
                        confidence=Confidence.HIGH,
                        source=self.module_name,
                        provider="macos_native",
                        summary="System Integrity Protection (SIP) is disabled",
                        details=(
                            "SIP prevents malicious software from modifying protected "
                            "files and folders on your Mac. Disabling SIP "
                            "significantly weakens system security."
                        ),
                        evidence={"sip": sip, "source_provider": "macos_native"},
                        tags=["sip", "macos", "os_hardening"],
                        recommended_action=(
                            "Re-enable System Integrity Protection via Recovery Mode "
                            "unless you have a specific security-reviewed "
                            "reason to keep it disabled."
                        ),
                        source_ref="macos_native:sip",
                    )
                )

            if filevault.get("available") is not False and not filevault.get(
                "enabled", True
            ):
                signals.append(
                    SignalCreate(
                        signal_type="disk_encryption_disabled",
                        category="device_security",
                        entity_type=EntityType.DEVICE,
                        entity_id=asset_id,
                        entity_value=asset_value,
                        user_id=user_id,
                        severity=Severity.HIGH,
                        confidence=Confidence.HIGH,
                        source=self.module_name,
                        provider="macos_native",
                        summary="FileVault disk encryption is not enabled",
                        details=(
                            "Without FileVault, data on this device is readable "
                            "without authentication if the disk is removed "
                            "or the device is stolen."
                        ),
                        evidence={
                            "filevault": filevault,
                            "source_provider": "macos_native",
                        },
                        tags=["filevault", "encryption", "macos", "os_hardening"],
                        recommended_action=(
                            "Enable FileVault in System Settings > Privacy & Security "
                            "to encrypt the startup disk."
                        ),
                        source_ref="macos_native:filevault",
                    )
                )

            if gatekeeper.get("available") is not False and not gatekeeper.get(
                "enabled", True
            ):
                signals.append(
                    SignalCreate(
                        signal_type="gatekeeper_disabled",
                        category="device_security",
                        entity_type=EntityType.DEVICE,
                        entity_id=asset_id,
                        entity_value=asset_value,
                        user_id=user_id,
                        severity=Severity.MEDIUM,
                        confidence=Confidence.HIGH,
                        source=self.module_name,
                        provider="macos_native",
                        summary="Gatekeeper is disabled — unsigned apps allowed to run",
                        details=(
                            "Gatekeeper checks apps for known malware and requires "
                            "notarisation. Disabling it allows execution of unsigned, "
                            "potentially malicious applications."
                        ),
                        evidence={
                            "gatekeeper": gatekeeper,
                            "source_provider": "macos_native",
                        },
                        tags=["gatekeeper", "macos", "os_hardening"],
                        recommended_action=(
                            "Re-enable Gatekeeper: run "
                            "`sudo spctl --master-enable` in Terminal."
                        ),
                        source_ref="macos_native:gatekeeper",
                    )
                )

        # --- lynis: hardening assessment ---
        lynis = LynisProvider()
        try:
            audit = await lynis.audit()
            hardening_index = audit.get("hardening_index", 0)
            suggestions = audit.get("suggestions", [])
            warnings = audit.get("warnings", [])

            # High-severity warnings from known dangerous test IDs
            high_warns = [
                w for w in warnings if any(id_ in w for id_ in _HIGH_SEVERITY_WARNINGS)
            ]
            severity = _lynis_severity(hardening_index, len(warnings))

            signals.append(
                SignalCreate(
                    signal_type="os_hardening_assessed",
                    category="device_security",
                    entity_type=EntityType.DEVICE,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=severity,
                    confidence=Confidence.HIGH,
                    source=self.module_name,
                    provider="lynis",
                    summary=(
                        f"Lynis hardening index: {hardening_index}/100 "
                        f"({len(warnings)} warnings, {len(suggestions)} suggestions)"
                    ),
                    details=(
                        f"System scored {hardening_index}/100 on the Lynis hardening "
                        f"index. {len(warnings)} warnings and {len(suggestions)} "
                        "suggestions were found."
                    ),
                    evidence={
                        "hardening_index": hardening_index,
                        "warning_count": len(warnings),
                        "suggestion_count": len(suggestions),
                        "high_severity_warnings": high_warns[:10],
                        "top_suggestions": suggestions[:10],
                        "source_provider": "lynis",
                    },
                    tags=["lynis", "hardening", "os_security"],
                    recommended_action=(
                        "Review lynis suggestions and address high-severity warnings. "
                        "Aim for a hardening index above 70."
                    ),
                    source_ref=f"lynis:hardening:{hardening_index}",
                )
            )
        except ProviderError as e:
            logger.warning("os_security.lynis_unavailable", error=str(e))

        logger.info(
            "os_security.completed",
            user_id=str(user_id),
            asset_id=str(asset_id),
            signals_emitted=len(signals),
        )
        return ModuleOutcome(signals=signals)
