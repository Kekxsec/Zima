# backend/app/providers/domain/sublist3r/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_sublist3r.py (MIT licensed)
# Copyright (c) Steve Micallef.
import json
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class Sublist3rProvider(BaseProviderClient):
    name = "sublist3r"
    base_url = "https://api.sublist3r.com/search.php"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def enumerate_subdomains(self, domain: str) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen: set[str] = set()

        domain = domain.strip().lower().strip(".")
        if not domain:
            return findings
        subdomains = await self._query(domain)
        for sub in subdomains:
            sub = sub.strip().lower().strip(".")
            if not sub or sub in seen:
                continue
            seen.add(sub)
            findings.append(
                dict(
                    provider=self.name,
                    category="subdomain_enumeration",
                    title="Subdomain found via Sublist3r",
                    description=f"Subdomain {sub} discovered for {domain}",
                    entity_type="hostname",
                    entity_value=sub,
                    confidence=0.65,
                    tags=["subdomain", "sublist3r", "passive"],
                )
            )
        if subdomains:
            evidence.append(
                dict(
                    source=self.name,
                    description=f"Sublist3r subdomain results for {domain}",
                    raw={"domain": domain, "count": len(subdomains)},
                    confidence=0.65,
                )
            )

        return findings

    async def _query(self, domain: str) -> list[str]:
        import urllib.parse

        url = f"{self.base_url}?domain={urllib.parse.quote(domain)}"
        try:
            response = await self._get(url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="Sublist3r request failed",
                retryable=True,
            ) from exc
        if response.status_code == 429:
            raise ProviderError(message="Sublist3r rate limited", retryable=True)
        if response.status_code >= 500:
            raise ProviderError(
                message="Sublist3r upstream unavailable",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code != 200:
            raise ProviderError(
                message="Sublist3r unexpected response",
                retryable=False,
                status_code=response.status_code,
            )
        if not response.content.strip():
            return []
        try:
            data = json.loads(response.content)
        except Exception as exc:
            raise ProviderError(
                message="Sublist3r JSON parse failed", retryable=False
            ) from exc
        if not isinstance(data, list):
            raise ProviderError(
                message="Sublist3r schema changed: expected list", retryable=False
            )
        return [str(x) for x in data if x]
