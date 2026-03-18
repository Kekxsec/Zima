# backend/app/providers/reputation/fraudguard/client.py
from __future__ import annotations

# Adapted from SpiderFoot module: modules/sfp_fraudguard.py (MIT licensed)
import base64
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class FraudguardProvider(BaseProviderClient):
    name = "fraudguard"
    base_url = "https://api.fraudguard.io/v2/ip"

    def __init__(
        self, api_user: str = "", api_password: str = "", timeout_seconds: int = 15
    ):
        self._api_user = api_user
        self._api_password = api_password
        self._timeout_seconds = timeout_seconds

    async def get_reputation(self, ip_address: str) -> list[dict[str, Any]]:
        api_user = str(self._api_user).strip()
        api_pass = str(self._api_password).strip()
        if not api_user or not api_pass:
            raise ProviderError(
                message="FraudGuard username and password are required", retryable=False
            )
        creds = base64.b64encode(f"{api_user}:{api_pass}".encode()).decode()
        headers = {"Accept": "application/json", "Authorization": f"Basic {creds}"}
        findings, evidence = [], []
        val = ip_address.strip()
        url = f"{self.base_url}/{val}"
        data = self._fetch(url, headers)
        if not isinstance(data, dict):
            return findings
        risk_level = str(data.get("risk_level", "")).strip()
        threat = str(data.get("threat", "")).strip()
        if risk_level and risk_level != "0":
            sev = "removed_severity" if risk_level in {"4", "5"} else "removed_severity"
            findings.append(
                dict(
                    provider=self.name,
                    category="threat_intel",
                    title=f"FraudGuard: {val}",
                    description=f"IP {val} risk level {risk_level}: {threat or 'suspicious'}",
                    severity=sev,
                    entity_type="ip_address",
                    entity_value=val,
                    confidence=0.78,
                    tags=["fraudguard", "threat_intel", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"FraudGuard data for {val}",
                    raw={"risk_level": risk_level, "threat": threat},
                    confidence=0.78,
                )
            )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Fraudguard", headers=headers, timeout=self._timeout_seconds
        )
