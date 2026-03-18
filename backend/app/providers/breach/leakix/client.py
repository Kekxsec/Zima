# backend/app/providers/breach/leakix/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_leakix.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class LeakixProvider(BaseProviderClient):
    name = "leakix"
    base_url = "https://leakix.net"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search_leaks(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(message="LeakIX API key is required", retryable=False)
        headers = {"api-key": api_key, "Accept": "application/json"}
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "ip_address"}:
                continue
            val = _value.strip()
            endpoint = "domain" if _entity_type == "domain" else "host"
            url = f"{self.base_url}/{endpoint}/{urllib.parse.quote(val)}"
            data = self._fetch(url, headers)
            services = (
                data
                if isinstance(data, list)
                else data.get("Services", []) or data.get("services", [])
            )
            if not isinstance(services, list):
                services = [data] if data else []
            leaks = [s for s in services if isinstance(s, dict) and s.get("leak")]
            if leaks:
                findings.append(
                    dict(
                        provider=self.name,
                        category="data_leak",
                        title=f"LeakIX: {len(leaks)} service leaks",
                        description=f"{val} has {len(leaks)} leaking services on LeakIX",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.80,
                        tags=["leakix", "data_leak", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"LeakIX data for {val}",
                        raw={"leak_count": len(leaks), "service_count": len(services)},
                        confidence=0.80,
                    )
                )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Leakix", headers=headers, timeout=self._timeout_seconds
        )
