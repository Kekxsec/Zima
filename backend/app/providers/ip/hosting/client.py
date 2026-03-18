# backend/app/providers/ip/hosting/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_hosting.py (MIT licensed)
import ipaddress
from typing import Any

DATACENTER_LIST_URL = (
    "https://raw.githubusercontent.com/client9/ipcat/master/datacenters.csv"
)


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class HostingProvider(BaseProviderClient):
    name = "hosting"

    def __init__(self, timeout_seconds: int = 30):
        self._timeout_seconds = timeout_seconds

    async def get_hosting_info(self, ip_address: str) -> list[dict[str, Any]]:
        findings, evidence = [], []
        try:
            resp = await self._get(DATACENTER_LIST_URL, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="Hosting list fetch failed", retryable=True
            ) from exc
        if resp.status_code != 200:
            raise ProviderError(
                message="Hosting list unexpected response", retryable=False
            )
        content = (
            resp.content
            if isinstance(resp.content, str)
            else resp.content.decode("utf-8", errors="replace")
        )
        # Parse CSV: start_ip,end_ip,name,url
        ranges = []
        for line in content.splitlines():
            parts = line.strip().split(",")
            if len(parts) >= 3 and not parts[0].startswith("#"):
                try:
                    start = int(ipaddress.ip_address(parts[0].strip()))
                    end = int(ipaddress.ip_address(parts[1].strip()))
                    name = parts[2].strip().strip('"')
                    ranges.append((start, end, name))
                except Exception:
                    pass

        val = ip_address.strip()
        try:
            ip_int = int(ipaddress.ip_address(val))
        except Exception:
            return findings
        for start, end, dc_name in ranges:
            if start <= ip_int <= end:
                findings.append(
                    dict(
                        provider=self.name,
                        category="hosting",
                        title=f"Datacenter IP: {val}",
                        description=f"IP {val} belongs to hosting provider/datacenter: {dc_name}",
                        entity_type="ip_address",
                        entity_value=val,
                        confidence=0.85,
                        tags=["hosting", "datacenter", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Datacenter for {val}",
                        raw={"datacenter": dc_name},
                        confidence=0.85,
                    )
                )
                break
        return findings
