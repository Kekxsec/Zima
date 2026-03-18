# backend/app/providers/ip/ipapicom/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_ipapicom.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class IPApiComProvider(BaseProviderClient):
    name = "ipapicom"
    base_url = "http://api.ipapi.com/api"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_geolocation(self, ip_address: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="ipapi.com API key is required",
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
        country_name = str(payload.get("country_name", "")).strip()
        if not country_name:
            return findings
        location_parts = [
            str(payload.get("city", "")).strip(),
            str(payload.get("region_name", "")).strip(),
            str(payload.get("region_code", "")).strip(),
            country_name,
            str(payload.get("country_code", "")).strip(),
        ]
        location = ", ".join(part for part in location_parts if part)
        findings.append(
            dict(
                provider=self.name,
                category="infrastructure_intel",
                title="IP geolocation enrichment from ipapi.com",
                description=f"ipapi.com geolocated {ip_value} to {location}",
                entity_type="ip_address",
                entity_value=ip_value,
                confidence=0.68,
                tags=["geoip", "ipapicom", "passive"],
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description=f"ipapi.com lookup for {ip_value}",
                raw=payload,
                confidence=0.68,
            )
        )
        return findings

    async def _query(self, ip_value: str, api_key: str) -> dict:
        query = urllib.parse.urlencode({"access_key": api_key})
        url = f"{self.base_url}/{ip_value}?{query}"
        payload = await self._get(url, label="IPApiCom", timeout=self._timeout_seconds)
        if not isinstance(payload, dict):
            raise ProviderError(
                message="ipapi.com schema changed: expected object payload",
                retryable=False,
            )
        return payload

    @staticmethod
    def _validate_ip(value: str) -> str:
        try:
            return str(ipaddress.ip_address(value.strip()))
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported input for ipapi.com: {value}",
                retryable=False,
            ) from exc
