# backend/app/providers/ip/isc/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_isc.py (MIT licensed)
from backend.app.providers.base.client import BaseProviderClient


class IscProvider(BaseProviderClient):
    name = "isc"
    base_url = "https://isc.sans.edu/api"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def get_isc_data(self, ip_address: str) -> list[dict[str, Any]]:
        findings, evidence = [], []
        val = ip_address.strip()
        url = f"{self.base_url}/ip/{val}?json"
        data = self._fetch(url)
        if not isinstance(data, dict):
            return findings
        ip_data = data.get("ip", {}) or data
        count = int(ip_data.get("count", 0) or 0)
        attacks = int(ip_data.get("attacks", 0) or 0)
        if count > 0 or attacks > 0:
            sev = "removed_severity" if attacks > 10 else "removed_severity"
            findings.append(
                dict(
                    provider=self.name,
                    category="threat_intel",
                    title=f"SANS ISC: {val}",
                    description=f"IP {val} seen {count} time(s) in SANS ISC reports, {attacks} attack(s) reported",
                    severity=sev,
                    entity_type="ip_address",
                    entity_value=val,
                    confidence=0.80,
                    tags=["isc", "sans", "threat_intel", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"SANS ISC data for {val}",
                    raw={"count": count, "attacks": attacks},
                    confidence=0.80,
                )
            )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Isc", timeout=self._timeout_seconds)
