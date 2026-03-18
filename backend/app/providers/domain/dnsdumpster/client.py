# backend/app/providers/domain/dnsdumpster/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_dnsdumpster.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class DnsdumpsterProvider(BaseProviderClient):
    name = "dnsdumpster"
    base_url = "https://api.hackertarget.com/hostsearch"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def resolve_dns(self, domain: str) -> list[dict[str, Any]]:
        findings, evidence = [], []
        seen: set[str] = set()
        val = domain.strip()
        url = f"{self.base_url}/?q={urllib.parse.quote(val)}"
        try:
            resp = await self._get(url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="DNSdumpster request failed", retryable=True
            ) from exc
        if resp.status_code == 429:
            raise ProviderError(message="DNSdumpster rate limited", retryable=True)
        if resp.status_code != 200:
            raise ProviderError(
                message="DNSdumpster unexpected response", retryable=False
            )
        content = (
            resp.content
            if isinstance(resp.content, str)
            else resp.content.decode("utf-8", errors="replace")
        )
        hosts = []
        for line in content.strip().splitlines():
            parts = line.split(",")
            if parts:
                host = parts[0].strip()
                if host and host not in seen and val in host:
                    seen.add(host)
                    hosts.append(host)
                    findings.append(
                        dict(
                            provider=self.name,
                            category="subdomain",
                            title=f"DNSdumpster: {host}",
                            description=f"Host found for {val}: {host}",
                            entity_type="hostname",
                            entity_value=host,
                            confidence=0.72,
                            tags=["dnsdumpster", "subdomain", "passive"],
                        )
                    )
            if hosts:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"DNSdumpster hosts for {val}",
                        raw={"count": len(hosts)},
                        confidence=0.72,
                    )
                )
        return findings
