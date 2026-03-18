# backend/app/providers/domain/projectdiscovery/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_projectdiscovery.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ProjectdiscoveryProvider(BaseProviderClient):
    name = "projectdiscovery"
    base_url = "https://dns.projectdiscovery.io/dns"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def enumerate_subdomains(self, domain: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="ProjectDiscovery API key is required", retryable=False
            )
        headers = {"Authorization": api_key, "Accept": "application/json"}
        findings, evidence = [], []
        seen: set[str] = set()
        val = domain.strip()
        url = f"{self.base_url}/{urllib.parse.quote(val)}/subdomains"
        data = self._fetch(url, headers)
        subdomains = data.get("subdomains", []) if isinstance(data, dict) else []
        if not isinstance(subdomains, list):
            return findings
        for sub in subdomains[:50]:
            host = str(sub).strip()
            if not host or host in seen:
                continue
            seen.add(host)
            fqdn = f"{host}.{val}" if not host.endswith(val) else host
            findings.append(
                dict(
                    provider=self.name,
                    category="subdomain",
                    title=f"ProjectDiscovery: {fqdn}",
                    description=f"Subdomain of {val} from ProjectDiscovery Chaos: {fqdn}",
                    entity_type="hostname",
                    entity_value=fqdn,
                    confidence=0.80,
                    tags=["projectdiscovery", "subdomain", "passive"],
                )
            )
            if subdomains:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"ProjectDiscovery subdomains for {val}",
                        raw={"count": len(subdomains)},
                        confidence=0.80,
                    )
                )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url,
            label="Projectdiscovery",
            headers=headers,
            timeout=self._timeout_seconds,
        )
