# backend/app/providers/reputation/seon/client.py
from __future__ import annotations

# Adapted from SpiderFoot module: modules/sfp_seon.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class SeonProvider(BaseProviderClient):
    name = "seon"
    base_url = "https://api.seon.io/SeonRestService"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_reputation(
        self,
        *,
        email: str | None = None,
        ip_address: str | None = None,
        phone_number: str | None = None,
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(message="SEON API key is required", retryable=False)
        headers = {
            "X-API-KEY": api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if email is not None:
            _inputs.append(("email", email))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        if phone_number is not None:
            _inputs.append(("phone_number", phone_number))
        for _entity_type, _value in _inputs:
            val = _value.strip()
            if _entity_type == "email":
                url = f"{self.base_url}/email-api/v2.0/{urllib.parse.quote(val)}"
            elif _entity_type == "ip_address":
                url = f"{self.base_url}/ip-api/v1.0/{urllib.parse.quote(val)}"
            elif _entity_type == "phone":
                url = f"{self.base_url}/phone-api/v1.0/{urllib.parse.quote(val)}"
            else:
                return findings
            data = self._fetch(url, headers)
            if not isinstance(data, dict):
                continue
            result = data.get("data", {}) or {}
            fraud_score = result.get("fraud_score")
            if fraud_score is not None:
                sev = (
                    "removed_severity"
                    if float(fraud_score) > 70
                    else (
                        "removed_severity"
                        if float(fraud_score) > 40
                        else "removed_severity"
                    )
                )
                findings.append(
                    dict(
                        provider=self.name,
                        category="fraud_score",
                        title=f"SEON: {val[:50]}",
                        description=f"SEON fraud score for {val}: {fraud_score}",
                        severity=sev,
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.78,
                        tags=["seon", "fraud", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"SEON data for {val}",
                        raw={"fraud_score": fraud_score},
                        confidence=0.78,
                    )
                )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Seon", headers=headers, timeout=self._timeout_seconds
        )
