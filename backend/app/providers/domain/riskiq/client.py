# backend/app/providers/domain/riskiq/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_riskiq.py (MIT licensed)
import base64
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class RiskiqProvider(BaseProviderClient):
    name = "riskiq"
    base_url = "https://api.passivetotal.org/v2"

    def __init__(
        self, api_user: str = "", api_key: str = "", timeout_seconds: int = 15
    ):
        self._api_user = api_user
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def lookup_domain(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        api_user = str(self._api_user).strip()
        api_key = str(self._api_key).strip()
        if not api_user or not api_key:
            raise ProviderError(
                message="RiskIQ user and API key are required", retryable=False
            )
        creds = base64.b64encode(f"{api_user}:{api_key}".encode()).decode()
        headers = {"Accept": "application/json", "Authorization": f"Basic {creds}"}
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
            url = f"{self.base_url}/dns/passive?query={urllib.parse.quote(val)}"
            data = self._fetch(url, headers)
            results = data.get("results", []) if isinstance(data, dict) else []
            if not isinstance(results, list):
                continue
            for rec in results[:20]:
                if not isinstance(rec, dict):
                    continue
                resolve = str(rec.get("resolve", "")).strip()
                if not resolve or resolve in seen:
                    continue
                seen.add(resolve)
                findings.append(
                    dict(
                        provider=self.name,
                        category="passive_dns",
                        title=f"RiskIQ: {resolve}",
                        description=f"RiskIQ passive DNS for {val}: {resolve}",
                        entity_type="hostname",
                        entity_value=resolve,
                        confidence=0.80,
                        tags=["riskiq", "passive_dns", "passive"],
                    )
                )
            if results:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"RiskIQ passive DNS for {val}",
                        raw={"count": len(results)},
                        confidence=0.80,
                    )
                )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Riskiq", headers=headers, timeout=self._timeout_seconds
        )
