# backend/app/modules/device/device_inventory/service.py
from __future__ import annotations

import uuid

from backend.app.core.enums import Confidence, EntityType, Severity
from backend.app.core.logging import get_logger
from backend.app.modules.base.service import BaseModuleService
from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.tools.osquery.client import OsqueryProvider
from backend.app.providers.tools.oui_master_database.client import (
    OuiMasterDatabaseProvider,
)
from backend.app.signals.schemas import SignalCreate

logger = get_logger(__name__)


class DeviceInventoryService(BaseModuleService):
    """Device network interface inventory with offline OUI vendor enrichment.

    Queries osquery for network interface details (MAC addresses, IPs, flags),
    then enriches each MAC address with IEEE OUI vendor lookup using the
    bundled offline database. Emits one inventory signal per interface.
    """

    module_name = "device_inventory"
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

        # --- osquery: network interface details ---
        osq = OsqueryProvider()
        interfaces: list[dict] = []
        try:
            interfaces = await osq.query_named("interface_details")
        except ProviderError as e:
            logger.warning("device_inventory.osquery_unavailable", error=str(e))

        if not interfaces:
            logger.info(
                "device_inventory.no_interfaces",
                user_id=str(user_id),
                asset_id=str(asset_id),
            )
            return signals

        # --- OUI vendor enrichment ---
        oui = OuiMasterDatabaseProvider()
        mac_addresses = [
            iface.get("mac", "") for iface in interfaces if iface.get("mac")
        ]
        vendor_map: dict[str, str] = {}
        if mac_addresses:
            try:
                results = await oui.lookup_many(mac_addresses)
                for r in results:
                    if r.get("mac"):
                        vendor_map[r["mac"]] = r.get("vendor", "")
            except Exception as e:
                logger.debug("device_inventory.oui_lookup_failed", error=str(e))

        # Emit one signal per interface
        for iface in interfaces:
            iface_name = iface.get("interface") or iface.get("name") or "unknown"
            mac = iface.get("mac", "")
            ip_address = iface.get("address") or iface.get("ip_address") or ""
            vendor = vendor_map.get(mac, "") if mac else ""

            # Skip loopback and virtual interfaces with no MAC
            if not mac or mac in ("00:00:00:00:00:00", ""):
                continue

            summary_parts = [f"Interface {iface_name}"]
            if mac:
                summary_parts.append(f"MAC {mac}")
                if vendor:
                    summary_parts.append(f"({vendor})")
            if ip_address:
                summary_parts.append(f"IP {ip_address}")

            signals.append(
                SignalCreate(
                    signal_type="network_interface_discovered",
                    category="device_inventory",
                    entity_type=EntityType.DEVICE,
                    entity_id=asset_id,
                    entity_value=asset_value,
                    user_id=user_id,
                    severity=Severity.INFO,
                    confidence=Confidence.HIGH,
                    source=self.module_name,
                    provider="osquery+oui_master_database",
                    summary=" — ".join(summary_parts),
                    details=(
                        f"Network interface '{iface_name}' found with "
                        f"MAC {mac or 'unknown'}. "
                        + (f"Vendor: {vendor}. " if vendor else "")
                        + (f"IP: {ip_address}." if ip_address else "")
                    ),
                    evidence={
                        "interface": iface,
                        "vendor": vendor,
                        "source_provider": "osquery+oui_master_database",
                    },
                    tags=["device_inventory", "network", "interface", iface_name],
                    recommended_action=(
                        "Review active network interfaces. Remove or disable unused "
                        "interfaces to reduce attack surface."
                    ),
                    source_ref=f"osquery:interface_details:{iface_name}:{mac}",
                )
            )

        logger.info(
            "device_inventory.completed",
            user_id=str(user_id),
            asset_id=str(asset_id),
            interfaces_found=len(interfaces),
            signals_emitted=len(signals),
        )
        return signals
