# backend/app/providers/domain/zetalytics/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_zetalytics.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ZetalyticsProvider(BaseProviderClient):
    name = "zetalytics"
    base_url = "https://zetalytics.com/api/v1"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def lookup_domain(
        self,
        *,
        domain: str | None = None,
        email: str | None = None,
        ip_address: str | None = None,
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="Zetalytics API key is required", retryable=False
            )
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            val = _value.strip()
            if _entity_type == "domain":
                url = f"{self.base_url}/hostname2ip/?q={urllib.parse.quote(val)}&token={api_key}"
            elif _entity_type == "ip_address":
                url = f"{self.base_url}/ip2hosts/?q={urllib.parse.quote(val)}&token={api_key}"
            elif _entity_type == "email":
                url = f"{self.base_url}/email2domain/?q={urllib.parse.quote(val)}&token={api_key}"
            else:
                return findings
            data = self._fetch(url)
            results = data.get("results", []) if isinstance(data, dict) else data
            if not isinstance(results, list):
                continue
            for item in results[:20]:
                if not isinstance(item, dict):
                    continue
                host = str(
                    item.get("qname", "")
                    or item.get("ip", "")
                    or item.get("domain", "")
                ).strip()
                if not host or host in seen:
                    continue
                seen.add(host)
                findings.append(
                    dict(
                        provider=self.name,
                        category="passive_dns",
                        title=f"Zetalytics passive DNS: {host}",
                        description=f"Zetalytics passive DNS record for {val}: {host}",
                        entity_type="hostname",
                        entity_value=host,
                        confidence=0.72,
                        tags=["zetalytics", "passive_dns", "passive"],
                    )
                )
            if results:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Zetalytics data for {val}",
                        raw={"count": len(results)},
                        confidence=0.72,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Zetalytics", timeout=self._timeout_seconds)
