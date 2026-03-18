# backend/app/providers/threat_intel/xforce/client.py
from __future__ import annotations

# Adapted from SpiderFoot module: modules/sfp_xforce.py (MIT licensed)
import base64
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class XforceProvider(BaseProviderClient):
    name = "xforce"
    base_url = "https://api.xforce.ibmcloud.com"

    def __init__(
        self, api_key: str = "", api_password: str = "", timeout_seconds: int = 15
    ):
        self._api_key = api_key
        self._api_password = api_password
        self._timeout_seconds = timeout_seconds

    async def check_reputation(
        self,
        *,
        domain: str | None = None,
        ip_address: str | None = None,
        url: str | None = None,
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        api_password = str(self._api_password).strip()
        if not api_key or not api_password:
            raise ProviderError(
                message="IBM X-Force API key and password are required", retryable=False
            )
        creds = base64.b64encode(f"{api_key}:{api_password}".encode()).decode()
        headers = {"Authorization": f"Basic {creds}", "Accept": "application/json"}
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        if url is not None:
            _inputs.append(("url", url))
        for _entity_type, _value in _inputs:
            val = _value.strip()
            if _entity_type == "ip_address":
                url = f"{self.base_url}/ipr/{urllib.parse.quote(val)}"
            elif _entity_type == "domain":
                url = f"{self.base_url}/resolve/{urllib.parse.quote(val)}"
            elif _entity_type == "url":
                url = f"{self.base_url}/url/{urllib.parse.quote(val)}"
            else:
                return findings
            data = self._fetch(url, headers)
            score = data.get("score") or data.get("result", {}).get("score")
            if score is not None:
                sev = (
                    "removed_severity"
                    if float(score) >= 7
                    else "removed_severity"
                    if float(score) >= 4
                    else "removed_severity"
                )
                findings.append(
                    dict(
                        provider=self.name,
                        category="threat_intelligence",
                        title=f"X-Force risk score: {score}",
                        description=f"{val} has X-Force risk score {score}/10",
                        severity=sev,
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.75,
                        tags=["xforce", "threat_intelligence", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"X-Force data for {val}",
                        raw={"score": score},
                        confidence=0.75,
                    )
                )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Xforce", headers=headers, timeout=self._timeout_seconds
        )
