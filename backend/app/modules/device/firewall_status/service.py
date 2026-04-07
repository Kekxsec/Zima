# backend/app/modules/device/firewall_status/service.py
from __future__ import annotations

import uuid

from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.tools.lynis.client import LynisProvider
from backend.app.providers.tools.osquery.client import OsqueryProvider
from backend.app.signals.schemas import SignalCreate

logger = get_logger(__name__)

# Lynis test IDs that indicate firewall-specific warnings
_FIREWALL_WARNING_IDS = frozenset(
    [
        "FIRE-4512",  # iptables not active
        "FIRE-4513",  # nftables not active
        "FIRE-4590",  # firewall software not found
        "NETW-3015",  # no firewall detected
    ]
)


class FirewallStatusService(BaseModuleService):
    """Firewall status assessment using osquery telemetry and lynis audit.

    Queries the iptables firewall rules via osquery (Linux), then checks
    the lynis audit report for firewall-specific warnings. Emits signals
    when no firewall rules are detected or lynis reports firewall issues.
    """

    module_name = "firewall_status"
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

        # --- osquery: iptables rules ---
        osq = OsqueryProvider()
        iptables_rows: list[dict] = []
        try:
            iptables_rows = await osq.query_named("iptables")
        except ProviderError as e:
            logger.debug("firewall_status.osquery_iptables_unavailable", error=str(e))

        if iptables_rows:
            # Count non-default-policy rules (chain rules with explicit targets)
            active_rules = [
                r for r in iptables_rows if r.get("target") not in ("", None)
            ]
            signals.append(
                SignalCreate(
                    signal_type="firewall_rules_detected",
                    category="device_security",
                    entity_type=EntityType.DEVICE,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=Severity.INFO,
                    confidence=Confidence.HIGH,
                    source=self.module_name,
                    provider="osquery",
                    summary=f"iptables: {len(active_rules)} active rules detected",
                    details=(
                        f"osquery found {len(iptables_rows)} total iptables entries, "
                        f"{len(active_rules)} with explicit targets."
                    ),
                    evidence={
                        "total_entries": len(iptables_rows),
                        "active_rules": len(active_rules),
                        "sample_rules": iptables_rows[:10],
                        "source_provider": "osquery",
                    },
                    tags=["firewall", "iptables", "osquery"],
                    recommended_action=(
                        "Review iptables rules to ensure only expected traffic "
                        "is permitted. Consider using ufw or firewalld for management."
                    ),
                    source_ref="osquery:iptables",
                )
            )
        elif iptables_rows is not None and len(iptables_rows) == 0:
            # osquery ran successfully but returned no rules
            signals.append(
                SignalCreate(
                    signal_type="firewall_no_rules_detected",
                    category="device_security",
                    entity_type=EntityType.DEVICE,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=Severity.MEDIUM,
                    confidence=Confidence.MEDIUM,
                    source=self.module_name,
                    provider="osquery",
                    summary="No iptables rules detected via osquery",
                    details=(
                        "osquery returned no iptables entries. The host firewall may "
                        "not be configured, or this is a non-Linux system."
                    ),
                    evidence={"source_provider": "osquery"},
                    tags=["firewall", "iptables", "osquery"],
                    recommended_action=(
                        "Verify that a host-based firewall "
                        "(ufw, firewalld, or iptables) is active "
                        "and configured with appropriate rules."
                    ),
                    source_ref="osquery:iptables:empty",
                )
            )

        # --- lynis: firewall audit warnings ---
        lynis = LynisProvider()
        try:
            audit = await lynis.audit()
            warnings = audit.get("warnings", [])
            suggestions = audit.get("suggestions", [])

            # Filter for firewall-relevant warnings
            fw_warnings = [
                w for w in warnings if any(id_ in w for id_ in _FIREWALL_WARNING_IDS)
            ]
            fw_suggestions = [
                s
                for s in suggestions
                if any(
                    kw in s.lower()
                    for kw in ("firewall", "iptables", "nftables", "ufw", "pf ")
                )
            ]

            if fw_warnings:
                signals.append(
                    SignalCreate(
                        signal_type="firewall_lynis_warnings",
                        category="device_security",
                        entity_type=EntityType.DEVICE,
                        entity_id=asset_id,
                        entity_value=asset_value,
                        user_id=user_id,
                        severity=Severity.HIGH,
                        confidence=Confidence.HIGH,
                        source=self.module_name,
                        provider="lynis",
                        summary=(
                            f"Lynis detected {len(fw_warnings)} firewall warning(s)"
                        ),
                        details=(
                            f"Lynis audit found {len(fw_warnings)} "
                            f"firewall-related warning(s) and "
                            f"{len(fw_suggestions)} suggestion(s)."
                        ),
                        evidence={
                            "firewall_warnings": fw_warnings[:10],
                            "firewall_suggestions": fw_suggestions[:10],
                            "source_provider": "lynis",
                        },
                        tags=["firewall", "lynis", "hardening"],
                        recommended_action=(
                            "Address the firewall warnings identified by Lynis. "
                            "Ensure a host-based firewall is active and "
                            "properly configured."
                        ),
                        source_ref="lynis:firewall_warnings",
                    )
                )
            elif fw_suggestions:
                signals.append(
                    SignalCreate(
                        signal_type="firewall_lynis_suggestions",
                        category="device_security",
                        entity_type=EntityType.DEVICE,
                        entity_id=asset_id,
                        entity_value=asset_value,
                        user_id=user_id,
                        severity=Severity.LOW,
                        confidence=Confidence.MEDIUM,
                        source=self.module_name,
                        provider="lynis",
                        summary=(
                            f"Lynis found {len(fw_suggestions)} "
                            f"firewall improvement suggestion(s)"
                        ),
                        details=(
                            "Lynis audit found no firewall warnings but identified "
                            f"{len(fw_suggestions)} suggestion(s) "
                            f"to improve firewall posture."
                        ),
                        evidence={
                            "firewall_suggestions": fw_suggestions[:10],
                            "source_provider": "lynis",
                        },
                        tags=["firewall", "lynis", "hardening"],
                        recommended_action=(
                            "Review Lynis firewall suggestions and apply "
                            "those relevant to your system's threat model."
                        ),
                        source_ref="lynis:firewall_suggestions",
                    )
                )
        except ProviderError as e:
            logger.warning("firewall_status.lynis_unavailable", error=str(e))

        logger.info(
            "firewall_status.completed",
            user_id=str(user_id),
            asset_id=str(asset_id),
            signals_emitted=len(signals),
        )
        return signals
