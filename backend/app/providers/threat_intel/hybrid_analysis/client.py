# backend/app/providers/threat_intel/hybrid_analysis/client.py
from __future__ import annotations

# Adapted from SpiderFoot module: modules/sfp_hybrid_analysis.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class HybridAnalysisProvider(BaseProviderClient):
    name = "hybrid_analysis"
    base_url = "https://www.hybrid-analysis.com/api/v2"

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
                message="Hybrid Analysis API key is required", retryable=False
            )
        headers = {
            "api-key": api_key,
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "Falcon Sandbox",
        }
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if hash_value is not None:
            _inputs.append(("hash_value", hash_value))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "ip_address", "hash"}:
                continue
            val = _value.strip()
            if _entity_type == "hash":
                term_type = "hash"
            elif _entity_type == "domain":
                term_type = "domain"
            else:
                term_type = "host"
            payload = urllib.parse.urlencode({term_type: val})
            url = f"{self.base_url}/search/terms"
            data = self._fetch_post(url, headers, payload)
            results = data.get("result", []) if isinstance(data, dict) else []
            if not isinstance(results, list):
                continue
            if results:
                verdicts = list(
                    {
                        str(r.get("verdict", ""))
                        for r in results
                        if isinstance(r, dict) and r.get("verdict")
                    }
                )
                malicious = any(v in {"malicious", "suspicious"} for v in verdicts)
                sev = "removed_severity" if malicious else "removed_severity"
                findings.append(
                    dict(
                        provider=self.name,
                        category="malware",
                        title=f"Hybrid Analysis: {val[:50]}",
                        description=f"{val} found in {len(results)} Hybrid Analysis submission(s). Verdicts: {', '.join(verdicts) or 'unknown'}",
                        severity=sev,
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.82,
                        tags=["hybrid_analysis", "malware", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Hybrid Analysis results for {val}",
                        raw={"count": len(results), "verdicts": verdicts},
                        confidence=0.82,
                    )
                )
        return findings

    async def _fetch_post(self, url: str, headers: dict, payload: str) -> dict:
        return await self._post(
            url,
            data=payload,
            label="HybridAnalysis",
            headers=headers,
            timeout=self._timeout_seconds,
        )
