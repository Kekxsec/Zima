# backend/app/providers/phone/numverify/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_numverify.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class NumverifyProvider(BaseProviderClient):
    name = "numverify"
    base_url = "https://apilayer.net/api/validate"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def validate_phone(self, phone_number: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="Numverify API key is required", retryable=False
            )
        findings, evidence = [], []
        val = phone_number.strip()
        url = f"{self.base_url}?{urllib.parse.urlencode({'access_key': api_key, 'number': val, 'format': '1'})}"
        data = self._fetch(url)
        if not isinstance(data, dict):
            return findings
        valid = data.get("valid", False)
        if valid:
            country = str(data.get("country_name", "")).strip()
            carrier = str(data.get("carrier", "")).strip()
            line_type = str(data.get("line_type", "")).strip()
            findings.append(
                dict(
                    provider=self.name,
                    category="phone_number",
                    title=f"Numverify: {val}",
                    description=f"Phone {val} is valid: {line_type} in {country}"
                    + (f" ({carrier})" if carrier else ""),
                    entity_type="phone",
                    entity_value=val,
                    confidence=0.85,
                    tags=["numverify", "phone", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"Numverify data for {val}",
                    raw={
                        "country": country,
                        "carrier": carrier,
                        "line_type": line_type,
                    },
                    confidence=0.85,
                )
            )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Numverify", timeout=self._timeout_seconds)
