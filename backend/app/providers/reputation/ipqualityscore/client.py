# backend/app/providers/reputation/ipqualityscore/client.py
from __future__ import annotations

# Adapted from SpiderFoot module: modules/sfp_ipqualityscore.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class IpqualityscoreProvider(BaseProviderClient):
    name = "ipqualityscore"
    base_url = "https://ipqualityscore.com/api/json"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_reputation(
        self,
        *,
        email: str | None = None,
        ip_address: str | None = None,
        phone_number: str | None = None,
        url: str | None = None,
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="IPQualityScore API key is required", retryable=False
            )
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if email is not None:
            _inputs.append(("email", email))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        if phone_number is not None:
            _inputs.append(("phone_number", phone_number))
        if url is not None:
            _inputs.append(("url", url))
        for _entity_type, _value in _inputs:
            val = urllib.parse.quote(_value.strip())
            if _entity_type == "ip_address":
                url = f"{self.base_url}/ip/{api_key}/{val}"
            elif _entity_type == "email":
                url = f"{self.base_url}/email/{api_key}/{val}"
            elif _entity_type == "url":
                url = f"{self.base_url}/url/{api_key}/{val}"
            elif _entity_type == "phone":
                url = f"{self.base_url}/phone/{api_key}/{val}"
            else:
                return findings
            data = self._fetch(url)
            fraud_score = data.get("fraud_score") or data.get("overall_score")
            if fraud_score is not None:
                score = int(fraud_score)
                sev = (
                    "removed_severity"
                    if score >= 75
                    else "removed_severity"
                    if score >= 50
                    else "removed_severity"
                )
                if score >= 25:
                    findings.append(
                        dict(
                            provider=self.name,
                            category="fraud_detection",
                            title=f"IPQualityScore: fraud score {score}",
                            description=f"{_value} has fraud score {score}/100",
                            severity=sev,
                            entity_type=_entity_type,
                            entity_value=_value,
                            confidence=min(1.0, score / 100 + 0.2),
                            tags=["ipqualityscore", "fraud", "passive"],
                        )
                    )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"IPQualityScore data for {_value}",
                        raw={
                            "fraud_score": score,
                            "proxy": data.get("proxy"),
                            "vpn": data.get("vpn"),
                        },
                        confidence=0.80,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(
            url, label="Ipqualityscore", timeout=self._timeout_seconds
        )
