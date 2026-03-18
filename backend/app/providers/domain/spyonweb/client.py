# backend/app/providers/domain/spyonweb/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_spyonweb.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class SpyonwebProvider(BaseProviderClient):
    name = "spyonweb"
    base_url = "https://api.spyonweb.com/v1"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def find_similar(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(message="SpyOnWeb API key is required", retryable=False)
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "ip_address"}:
                continue
            val = _value.strip()
            if _entity_type == "domain":
                url = f"{self.base_url}/domain/{urllib.parse.quote(val)}?access_token={api_key}"
            else:
                url = f"{self.base_url}/ip/{urllib.parse.quote(val)}?access_token={api_key}"
            data = self._fetch(url)
            if not isinstance(data, dict):
                continue
            result = data.get("result", {}) or {}
            domains = list(result.keys()) if isinstance(result, dict) else []
            for domain in domains[:20]:
                if domain in seen:
                    continue
                seen.add(domain)
                findings.append(
                    dict(
                        provider=self.name,
                        category="co_hosted",
                        title=f"SpyOnWeb: {domain}",
                        description=f"Domain {domain} shares analytics/IP with {val}",
                        entity_type="domain",
                        entity_value=domain,
                        confidence=0.72,
                        tags=["spyonweb", "co_hosted", "passive"],
                    )
                )
            if domains:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"SpyOnWeb results for {val}",
                        raw={"count": len(domains)},
                        confidence=0.72,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Spyonweb", timeout=self._timeout_seconds)
