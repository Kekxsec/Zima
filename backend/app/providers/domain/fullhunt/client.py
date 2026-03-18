# backend/app/providers/domain/fullhunt/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_fullhunt.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class FullHuntProvider(BaseProviderClient):
    name = "fullhunt"
    base_url = "https://fullhunt.io/api/v1"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def enumerate_subdomains(self, domain: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(message="FullHunt API key is required", retryable=False)
        headers = {"X-API-KEY": api_key, "Accept": "application/json"}
        findings, evidence = [], []
        seen: set[str] = set()
        if not domain:
            return findings
        domain = domain.strip().lower().strip(".")
        url = f"{self.base_url}/domain/{urllib.parse.quote(domain)}/subdomains"
        data = await self._fetch(url, headers)
        hosts = data.get("hosts", [])
        if not isinstance(hosts, list):
            return findings
        for host in hosts:
            h = str(host).strip().lower().strip(".")
            if not h or h in seen:
                continue
            seen.add(h)
            findings.append(
                dict(
                    provider=self.name,
                    category="subdomain_enumeration",
                    title=f"FullHunt subdomain: {h}",
                    description=f"Subdomain {h} found for {domain}",
                    entity_type="hostname",
                    entity_value=h,
                    confidence=0.78,
                    tags=["fullhunt", "subdomain", "passive"],
                )
            )
        if hosts:
            evidence.append(
                dict(
                    source=self.name,
                    description=f"FullHunt subdomains for {domain}",
                    raw={"count": len(hosts)},
                    confidence=0.78,
                )
            )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="FullHunt", headers=headers, timeout=self._timeout_seconds
        )
