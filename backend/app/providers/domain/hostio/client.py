# backend/app/providers/domain/hostio/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_hostio.py (MIT licensed)
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class HostioProvider(BaseProviderClient):
    name = "hostio"
    base_url = "https://host.io/api"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def lookup_domain(self, domain: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(message="host.io API key is required", retryable=False)
        headers = {"Authorization": f"Bearer {api_key}"}
        findings, evidence = [], []
        val = domain.strip()
        url = f"{self.base_url}/full/{val}"
        data = self._fetch(url, headers)
        if not isinstance(data, dict):
            return findings
        # Extract IPs, related domains, emails
        domain_data = data.get("domain", {}) or {}
        ipv4 = domain_data.get("ipv4", []) or []
        related = list((data.get("related", {}) or {}).get("domains", []) or [])[:10]
        rank = (
            data.get("web", {}).get("rank")
            if isinstance(data.get("web"), dict)
            else None
        )
        if ipv4 or related:
            desc = f"host.io data for {val}: {len(ipv4)} IPs"
            if related:
                desc += f", {len(related)} related domains"
            if rank:
                desc += f", rank #{rank}"
            findings.append(
                dict(
                    provider=self.name,
                    category="network_info",
                    title=f"host.io: {val}",
                    description=desc,
                    entity_type="domain",
                    entity_value=val,
                    confidence=0.78,
                    tags=["hostio", "passive_dns", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"host.io data for {val}",
                    raw={"ipv4": ipv4[:5], "related_count": len(related), "rank": rank},
                    confidence=0.78,
                )
            )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Hostio", headers=headers, timeout=self._timeout_seconds
        )
