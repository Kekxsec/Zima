# backend/app/providers/social/nameapi/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_nameapi.py (MIT licensed)
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class NameapiProvider(BaseProviderClient):
    name = "nameapi"
    base_url = "https://api.nameapi.org/rest/v5.3"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_contact_info(self, email: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(message="NameAPI key is required", retryable=False)
        findings, evidence = [], []
        val = email.strip()
        url = f"{self.base_url}/email/disposableemailaddressdetector?apiKey={api_key}"
        payload = {"inputEmail": {"address": val}}
        data = self._fetch_post(url, payload)
        if not isinstance(data, dict):
            return findings
        disposable = str(data.get("disposable", "NO")).strip().upper()
        if disposable == "YES":
            findings.append(
                dict(
                    provider=self.name,
                    category="email_reputation",
                    title=f"NameAPI disposable: {val}",
                    description=f"Email {val} identified as disposable by NameAPI",
                    entity_type="email",
                    entity_value=val,
                    confidence=0.80,
                    tags=["nameapi", "disposable", "email", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"NameAPI disposable check for {val}",
                    raw={"disposable": True},
                    confidence=0.80,
                )
            )
        return findings

    async def _fetch_post(self, url: str, payload: dict) -> dict:
        return await self._post(
            url, json_data=payload, label="Nameapi", timeout=self._timeout_seconds
        )
