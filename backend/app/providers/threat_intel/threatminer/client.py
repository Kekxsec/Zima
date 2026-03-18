# backend/app/providers/threat_intel/threatminer/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_threatminer.py (MIT licensed)
# Copyright (c) Steve Micallef.
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class ThreatMinerProvider(BaseProviderClient):
    name = "threatminer"
    base_url = "https://api.threatminer.org/v2"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def check_reputation(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen: set[str] = set()

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type == "domain":
                endpoint = f"{self.base_url}/domain.php?q={urllib.parse.quote(_value.strip())}&rt=2"
                etype = "domain"
            elif _entity_type == "ip_address":
                endpoint = f"{self.base_url}/host.php?q={urllib.parse.quote(_value.strip())}&rt=2"
                etype = "ip"
            else:
                return findings

            data = self._fetch(endpoint)
            results = data.get("results", [])
            if not isinstance(results, list):
                continue
            for item in results:
                if not isinstance(item, dict):
                    continue
                domain = str(item.get("domain", "") or item.get("ip", "")).strip()
                if not domain or domain in seen:
                    continue
                seen.add(domain)
                findings.append(
                    dict(
                        provider=self.name,
                        category="threat_intelligence",
                        title=f"ThreatMiner association: {domain}",
                        description=f"{_value} associated with {domain} via ThreatMiner",
                        entity_type="domain" if etype == "domain" else "ip_address",
                        entity_value=domain,
                        confidence=0.62,
                        tags=["threatminer", "threat_intelligence", "passive"],
                    )
                )
            if results:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"ThreatMiner results for {_value}",
                        raw={"count": len(results)},
                        confidence=0.62,
                    )
                )

        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="ThreatMiner", timeout=self._timeout_seconds)
