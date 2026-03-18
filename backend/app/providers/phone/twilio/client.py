# backend/app/providers/phone/twilio/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_twilio.py (MIT licensed)
import base64
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class TwilioProvider(BaseProviderClient):
    name = "twilio"
    base_url = "https://lookups.twilio.com/v1/PhoneNumbers"

    def __init__(
        self, account_sid: str = "", auth_token: str = "", timeout_seconds: int = 15
    ):
        self._account_sid = account_sid
        self._auth_token = auth_token
        self._timeout_seconds = timeout_seconds

    async def lookup_phone(self, phone_number: str) -> list[dict[str, Any]]:
        account_sid = str(self._account_sid).strip()
        auth_token = str(self._auth_token).strip()
        if not account_sid or not auth_token:
            raise ProviderError(
                message="Twilio account SID and auth token are required",
                retryable=False,
            )
        creds = base64.b64encode(f"{account_sid}:{auth_token}".encode()).decode()
        headers = {"Authorization": f"Basic {creds}", "Accept": "application/json"}
        findings, evidence = [], []
        val = phone_number.strip()
        url = f"{self.base_url}/{urllib.parse.quote(val)}?Type=carrier&Type=caller-name"
        data = self._fetch(url, headers)
        if not isinstance(data, dict):
            return findings
        carrier = data.get("carrier", {}) or {}
        caller_name = data.get("caller_name", {}) or {}
        carrier_name = str(carrier.get("name", "")).strip()
        caller = str(caller_name.get("caller_name", "")).strip()
        line_type = str(carrier.get("type", "")).strip()
        if carrier_name or caller:
            findings.append(
                dict(
                    provider=self.name,
                    category="phone_number",
                    title=f"Twilio: {val}",
                    description=f"Phone {val}: {line_type}"
                    + (f" carrier={carrier_name}" if carrier_name else "")
                    + (f" caller={caller}" if caller else ""),
                    entity_type="phone",
                    entity_value=val,
                    confidence=0.85,
                    tags=["twilio", "phone", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"Twilio lookup for {val}",
                    raw={
                        "carrier": carrier_name,
                        "caller_name": caller,
                        "line_type": line_type,
                    },
                    confidence=0.85,
                )
            )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Twilio", headers=headers, timeout=self._timeout_seconds
        )
