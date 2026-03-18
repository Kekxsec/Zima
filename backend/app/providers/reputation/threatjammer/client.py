# backend/app/providers/reputation/threatjammer/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity = FindingSeverity.HIGH if (isinstance(score, (int, float)) and score >= 70) else FindingSeverity.MEDIUM
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_threatjammer.py (MIT licensed)
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ThreatjammerProvider(BaseProviderClient):
    name = "threatjammer"
    base_url = "https://dublin.api.threatjammer.com/v1"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_reputation(self, ip_address: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="ThreatJammer API key is required", retryable=False
            )
        headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
        findings, evidence = [], []
        val = ip_address.strip()
        url = f"{self.base_url}/ip/{val}"
        data = self._fetch(url, headers)
        if not isinstance(data, dict):
            return findings
        score = data.get("score", 0)
        risk = str(data.get("risk", "")).strip()
        datasets = data.get("datasets", []) or []
        if score or risk:
            findings.append(
                dict(
                    provider=self.name,
                    category="threat_intelligence",
                    title=f"ThreatJammer: {val}",
                    description=f"IP {val} has ThreatJammer score {score}, risk: {risk}",
                    entity_type="ip_address",
                    entity_value=val,
                    confidence=0.80,
                    tags=["threatjammer", "threat_intel", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"ThreatJammer assessment for {val}",
                    raw={"score": score, "risk": risk, "datasets": datasets[:5]},
                    confidence=0.80,
                )
            )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Threatjammer", headers=headers, timeout=self._timeout_seconds
        )
