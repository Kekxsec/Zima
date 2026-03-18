# backend/app/providers/threat_intel/googlesafebrowsing/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_googlesafebrowsing.py (MIT licensed)
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class GooglesafebrowsingProvider(BaseProviderClient):
    name = "googlesafebrowsing"
    base_url = "https://safebrowsing.googleapis.com/v4/threatMatches:find"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def check_reputation(
        self, *, domain: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="Google Safe Browsing API key is required", retryable=False
            )
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if url is not None:
            _inputs.append(("url", url))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"url", "domain"}:
                continue
            val = _value.strip()
            url_to_check = val if _entity_type == "url" else f"http://{val}/"
            url = f"{self.base_url}?key={api_key}"
            payload = {
                "client": {"clientId": "SpiderFoot", "clientVersion": "3.2"},
                "threatInfo": {
                    "threatTypes": [
                        "MALWARE",
                        "SOCIAL_ENGINEERING",
                        "UNWANTED_SOFTWARE",
                    ],
                    "platformTypes": ["ANY_PLATFORM"],
                    "threatEntryTypes": ["URL"],
                    "threatEntries": [{"url": url_to_check}],
                },
            }
            data = self._fetch_post(url, payload)
            if not isinstance(data, dict):
                continue
            matches = data.get("matches", [])
            if matches:
                threat_types = list(
                    {
                        str(m.get("threatType", ""))
                        for m in matches
                        if isinstance(m, dict)
                    }
                )
                findings.append(
                    dict(
                        provider=self.name,
                        category="malware",
                        title=f"GSB threat: {val[:60]}",
                        description=f"Google Safe Browsing threat for {val}: {', '.join(threat_types)}",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.90,
                        tags=["googlesafebrowsing", "malware", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Google Safe Browsing match for {val}",
                        raw={"threats": threat_types},
                        confidence=0.90,
                    )
                )
        return findings

    async def _fetch_post(self, url: str, payload: dict) -> dict:
        return await self._post(
            url,
            json_data=payload,
            label="Googlesafebrowsing",
            timeout=self._timeout_seconds,
        )
