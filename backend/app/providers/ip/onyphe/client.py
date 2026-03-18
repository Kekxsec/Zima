# backend/app/providers/ip/onyphe/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM if any(t in {"malicious","botnet","scanner"} for t in ctags) else FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_onyphe.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class OnypheProvider(BaseProviderClient):
    name = "onyphe"
    base_url = "https://www.onyphe.io/api/v2"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search_hosts(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(message="Onyphe API key is required", retryable=False)
        headers = {"Authorization": f"apikey {api_key}", "Accept": "application/json"}
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"ip_address", "domain"}:
                continue
            val = _value.strip()
            cat = "ip" if _entity_type == "ip_address" else "domain"
            url = f"{self.base_url}/simple/{cat}/{urllib.parse.quote(val)}"
            data = self._fetch(url, headers)
            results = data.get("results", [])
            if not isinstance(results, list):
                continue
            ctags = set()
            for r in results[:20]:
                if isinstance(r, dict):
                    for t in r.get("tag") or []:
                        ctags.add(str(t))
            if ctags:
                findings.append(
                    dict(
                        provider=self.name,
                        category="threat_intelligence",
                        title=f"Onyphe tags for {val}",
                        description=f"{val} has Onyphe tags: {', '.join(sorted(ctags)[:10])}",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.72,
                        tags=["onyphe", "threat_intelligence", "passive"],
                    )
                )
            if results:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Onyphe data for {val}",
                        raw={"count": len(results), "tags": list(ctags)[:20]},
                        confidence=0.72,
                    )
                )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Onyphe", headers=headers, timeout=self._timeout_seconds
        )
