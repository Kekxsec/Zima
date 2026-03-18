# backend/app/providers/breach/citadel/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_citadel.py (MIT licensed)
from backend.app.providers.base.client import BaseProviderClient


class CitadelProvider(BaseProviderClient):
    name = "citadel"
    base_url = "https://leak-lookup.com/api"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search_breaches(self, email: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        findings, evidence = [], []
        val = email.strip()
        params = {"query": val, "type": "email_address"}
        if api_key:
            params["key"] = api_key
        data = self._fetch(self.base_url + "/search", params)
        if not isinstance(data, dict):
            return findings
        error = data.get("error")
        if error:
            return findings
        results = data.get("message", {})
        if isinstance(results, dict) and results:
            db_count = len(results)
            findings.append(
                dict(
                    provider=self.name,
                    category="credential_leak",
                    title=f"Leak-Lookup: {val}",
                    description=f"Email {val} found in {db_count} breach database(s) via Leak-Lookup",
                    entity_type="email",
                    entity_value=val,
                    confidence=0.80,
                    tags=["citadel", "leak", "breach", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"Leak-Lookup results for {val}",
                    raw={"databases": db_count},
                    confidence=0.80,
                )
            )
        return findings

    async def _fetch(self, url: str, params: dict) -> dict:
        return await self._post(
            url, json_data=params, label="Citadel", timeout=self._timeout_seconds
        )
