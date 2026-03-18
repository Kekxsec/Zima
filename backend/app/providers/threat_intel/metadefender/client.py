# backend/app/providers/threat_intel/metadefender/client.py
from __future__ import annotations

# Adapted from SpiderFoot module: modules/sfp_metadefender.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class MetadefenderProvider(BaseProviderClient):
    name = "metadefender"
    base_url = "https://api.metadefender.com/v4"

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
        if not api_key:
            raise ProviderError(
                message="MetaDefender API key is required", retryable=False
            )
        headers = {"apikey": api_key, "Accept": "application/json"}
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
                url = f"{self.base_url}/domain/{urllib.parse.quote(val)}"
            elif _entity_type == "hash":
                url = f"{self.base_url}/hash/{urllib.parse.quote(val)}"
            else:
                return findings
            data = self._fetch(url, headers)
            if not isinstance(data, dict):
                continue
            lookup = data.get("lookup_results", {}) or {}
            detected_by = int(lookup.get("detected_by", 0) or 0)
            sources = lookup.get("sources", []) or []
            if detected_by > 0 or sources:
                sev = "removed_severity" if detected_by > 2 else "removed_severity"
                findings.append(
                    dict(
                        provider=self.name,
                        category="threat_intel",
                        title=f"MetaDefender: {val[:50]}",
                        description=f"MetaDefender: {val} detected by {detected_by} source(s)",
                        severity=sev,
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.82,
                        tags=["metadefender", "threat_intel", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"MetaDefender data for {val}",
                        raw={"detected_by": detected_by},
                        confidence=0.82,
                    )
                )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Metadefender", headers=headers, timeout=self._timeout_seconds
        )
