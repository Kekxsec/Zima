# backend/app/providers/ip/ipinfo/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_ipinfo.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class IPInfoProvider(BaseProviderClient):
    name = "ipinfo"
    base_url = "https://ipinfo.io"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_geolocation(self, ip_address: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="IPinfo API key is required",
                retryable=False,
            )
        findings = []
        evidence = []
        seen = set()
        ip_value = self._validate_ip(ip_address)
        if ip_value in seen:
            return findings
        seen.add(ip_value)
        payload = await self._query(ip_value, api_key)
        if not payload:
            return findings
        country = str(payload.get("country", "")).strip()
        if not country:
            return findings
        location_parts = [
            str(payload.get("city", "")).strip(),
            str(payload.get("region", "")).strip(),
            country,
        ]
        location = ", ".join(part for part in location_parts if part)
        findings.append(
            dict(
                provider=self.name,
                category="infrastructure_intel",
                title="IP geolocation enrichment from IPinfo",
                description=f"IPinfo geolocated {ip_value} to {location}",
                entity_type="ip_address",
                entity_value=ip_value,
                confidence=0.7,
                tags=["geoip", "ipinfo", "passive"],
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description=f"IPinfo lookup for {ip_value}",
                raw=payload,
                confidence=0.7,
            )
        )
        return findings

    async def _query(self, ip_value: str, api_key: str) -> dict:
        url = f"{self.base_url}/{ip_value}/json"
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = await self._get(
            url, label="IPInfo", headers=headers, timeout=self._timeout_seconds
        )
        if not isinstance(payload, dict):
            raise ProviderError(
                message="IPinfo schema changed: expected object payload",
                retryable=False,
            )
        return payload

    @staticmethod
    def _validate_ip(value: str) -> str:
        try:
            return str(ipaddress.ip_address(value.strip()))
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported input for IPinfo: {value}",
                retryable=False,
            ) from exc
