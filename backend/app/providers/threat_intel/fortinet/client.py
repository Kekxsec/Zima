# backend/app/providers/threat_intel/fortinet/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_fortinet.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class FortinetProvider(BaseProviderClient):
    name = "fortinet"
    base_url = "https://www.fortiguard.com/search"
    signature_text = "Your signature is on the blocklist"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def check_reputation(self, ip_address: str) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen = set()
        ip_value = self._validate_ip(ip_address)
        if ip_value in seen:
            return findings
        seen.add(ip_value)
        matched = await self._query(ip_value)
        if not matched:
            return findings
        findings.append(
            dict(
                provider=self.name,
                category="reputation",
                title="IP listed in FortiGuard Antispam",
                description=f"{ip_value} matched FortiGuard Antispam blocklist signature",
                entity_type="ip_address",
                entity_value=ip_value,
                confidence=0.77,
                tags=["reputation", "fortinet", "malicious", "passive"],
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description=f"FortiGuard Antispam lookup for {ip_value}",
                raw={"ip": ip_value, "engine": 8},
                confidence=0.77,
            )
        )
        return findings

    async def _query(self, ip_value: str) -> bool:
        query = urllib.parse.urlencode({"q": ip_value, "engine": "8"})
        url = f"{self.base_url}?{query}"
        try:
            response = await self._get(url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="FortiGuard request failed",
                retryable=True,
            ) from exc
        if response.status_code == 429:
            raise ProviderError(
                message="FortiGuard rate limited request",
                retryable=True,
            )
        if response.status_code >= 500:
            raise ProviderError(
                message="FortiGuard upstream unavailable",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code != 200:
            raise ProviderError(
                message="FortiGuard returned unexpected response",
                retryable=False,
                status_code=response.status_code,
            )
        if not response.content.strip():
            return False
        return self.signature_text.lower() in response.content.lower()

    @staticmethod
    def _validate_ip(value: str) -> str:
        try:
            return str(ipaddress.ip_address(value.strip()))
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported input for Fortinet: {value}",
                retryable=False,
            ) from exc
