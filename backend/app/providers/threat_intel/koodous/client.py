# backend/app/providers/threat_intel/koodous/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH if malicious else FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_koodous.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class KoodousProvider(BaseProviderClient):
    name = "koodous"
    base_url = "https://analyst.koodous.com/api/apks"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def check_malware(
        self, *, domain: str | None = None, hash_value: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(message="Koodous API key is required", retryable=False)
        headers = {"Authorization": f"Token {api_key}", "Accept": "application/json"}
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if hash_value is not None:
            _inputs.append(("hash_value", hash_value))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"hash", "domain"}:
                continue
            val = _value.strip()
            if _entity_type == "hash":
                url = f"{self.base_url}?{urllib.parse.urlencode({'search': val})}"
            else:
                url = f"{self.base_url}?{urllib.parse.urlencode({'search': val})}"
            data = self._fetch(url, headers)
            results = data.get("results", []) if isinstance(data, dict) else []
            if not isinstance(results, list):
                continue
            if results:
                malicious = sum(
                    1 for r in results if isinstance(r, dict) and r.get("detected")
                )
                findings.append(
                    dict(
                        provider=self.name,
                        category="malware",
                        title=f"Koodous: {val[:50]}",
                        description=f"Koodous: {val} found in {len(results)} Android APK(s), {malicious} detected as malicious",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.78,
                        tags=["koodous", "android", "malware", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Koodous results for {val}",
                        raw={"count": len(results), "malicious": malicious},
                        confidence=0.78,
                    )
                )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Koodous", headers=headers, timeout=self._timeout_seconds
        )
