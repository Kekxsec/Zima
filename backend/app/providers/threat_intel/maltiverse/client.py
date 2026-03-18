# backend/app/providers/threat_intel/maltiverse/client.py
from __future__ import annotations

# Adapted from SpiderFoot module: modules/sfp_maltiverse.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class MaltiverseProvider(BaseProviderClient):
    name = "maltiverse"
    base_url = "https://api.maltiverse.com"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_report(
        self,
        *,
        domain: str | None = None,
        hash_value: str | None = None,
        ip_address: str | None = None,
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        headers: dict = {"Accept": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if hash_value is not None:
            _inputs.append(("hash_value", hash_value))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            val = _value.strip()
            if _entity_type == "ip_address":
                url = f"{self.base_url}/ip/{urllib.parse.quote(val)}"
            elif _entity_type == "domain":
                url = f"{self.base_url}/hostname/{urllib.parse.quote(val)}"
            elif _entity_type == "hash":
                url = f"{self.base_url}/sample/{urllib.parse.quote(val)}"
            else:
                return findings
            data = self._fetch(url, headers)
            if not isinstance(data, dict):
                continue
            classification = str(data.get("classification", "") or "").strip()
            is_malicious = classification in {"malicious", "suspicious"}
            bl_count = len(data.get("blacklist", []) or [])
            if is_malicious or bl_count > 0:
                sev = "removed_severity" if is_malicious else "removed_severity"
                findings.append(
                    dict(
                        provider=self.name,
                        category="threat_intel",
                        title=f"Maltiverse: {val[:50]}",
                        description=f"Maltiverse: {val} classification={classification or 'unknown'}, blacklists={bl_count}",
                        severity=sev,
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.80,
                        tags=["maltiverse", "threat_intel", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Maltiverse data for {val}",
                        raw={"classification": classification, "blacklists": bl_count},
                        confidence=0.80,
                    )
                )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Maltiverse", headers=headers, timeout=self._timeout_seconds
        )
