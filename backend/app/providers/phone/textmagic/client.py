# backend/app/providers/phone/textmagic/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_textmagic.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class TextmagicProvider(BaseProviderClient):
    name = "textmagic"
    base_url = "https://rest.textmagic.com/api/v2"

    def __init__(
        self, api_user: str = "", api_key: str = "", timeout_seconds: int = 15
    ):
        self._api_user = api_user
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def send_verification(self, phone_number: str) -> list[dict[str, Any]]:
        api_user = str(self._api_user).strip()
        api_key = str(self._api_key).strip()
        if not api_user or not api_key:
            raise ProviderError(
                message="TextMagic username and API key are required", retryable=False
            )
        headers = {
            "X-TM-Username": api_user,
            "X-TM-Key": api_key,
            "Accept": "application/json",
        }
        findings, evidence = [], []
        val = phone_number.strip()
        url = f"{self.base_url}/lookups/{urllib.parse.quote(val)}"
        data = self._fetch(url, headers)
        if not isinstance(data, dict):
            return findings
        carrier = str(data.get("carrier", "")).strip()
        country = str(
            data.get("country", {}).get("name", "")
            if isinstance(data.get("country"), dict)
            else ""
        ).strip()
        phone_type = str(data.get("type", "")).strip()
        if carrier or country:
            findings.append(
                dict(
                    provider=self.name,
                    category="phone_number",
                    title=f"TextMagic: {val}",
                    description=f"Phone {val}: {phone_type} in {country}"
                    + (f" ({carrier})" if carrier else ""),
                    entity_type="phone",
                    entity_value=val,
                    confidence=0.82,
                    tags=["textmagic", "phone", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"TextMagic lookup for {val}",
                    raw={"carrier": carrier, "country": country, "type": phone_type},
                    confidence=0.82,
                )
            )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Textmagic", headers=headers, timeout=self._timeout_seconds
        )
