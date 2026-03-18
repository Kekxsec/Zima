# backend/app/providers/threat_intel/pulsedive/client.py
from __future__ import annotations

# Adapted from SpiderFoot module: modules/sfp_pulsedive.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class PulsediveProvider(BaseProviderClient):
    name = "pulsedive"
    base_url = "https://pulsedive.com/api/info.php"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def check_reputation(
        self,
        *,
        domain: str | None = None,
        ip_address: str | None = None,
        url: str | None = None,
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        if url is not None:
            _inputs.append(("url", url))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"ip_address", "domain", "url"}:
                continue
            params = {"indicator": _value.strip(), "pretty": "1"}
            if api_key:
                params["key"] = api_key
            url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
            data = self._fetch(url)
            risk = str(data.get("risk", "")).strip()
            data.get("risk_recommended") or data.get("riskfactors")
            if risk and risk not in {"none", "unknown", ""}:
                sev = {
                    "critical": "removed_severity",
                    "high": "removed_severity",
                    "medium": "removed_severity",
                    "low": "removed_severity",
                }.get(risk.lower(), "removed_severity")
                findings.append(
                    dict(
                        provider=self.name,
                        category="threat_intelligence",
                        title=f"Pulsedive risk: {risk}",
                        description=f"{_value} has Pulsedive risk level: {risk}",
                        severity=sev,
                        entity_type=_entity_type,
                        entity_value=_value,
                        confidence=0.72,
                        tags=["pulsedive", "threat_intelligence", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Pulsedive data for {_value}",
                        raw={"risk": risk},
                        confidence=0.72,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Pulsedive", timeout=self._timeout_seconds)
