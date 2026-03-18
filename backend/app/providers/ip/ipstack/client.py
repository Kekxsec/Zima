# backend/app/providers/ip/ipstack/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_ipstack.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class IPStackProvider(BaseProviderClient):
    name = "ipstack"
    base_url = "http://api.ipstack.com"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_geolocation(self, ip_address: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="ipstack API key is required",
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
        findings.append(
            dict(
                provider=self.name,
                category="infrastructure_intel",
                title="IP geolocation enrichment from ipstack",
                description=f"ipstack geolocated {ip_value} to {country_name}",
                entity_type="ip_address",
                entity_value=ip_value,
                confidence=0.66,
                tags=["geoip", "ipstack", "passive"],
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description=f"ipstack lookup for {ip_value}",
                raw=payload,
                confidence=0.66,
            )
        )
        return findings

    async def _query(self, ip_value: str, api_key: str) -> dict:
        query = urllib.parse.urlencode({"access_key": api_key})
        url = f"{self.base_url}/{ip_value}?{query}"
        payload = await self._get(url, label="IPStack", timeout=self._timeout_seconds)
        if not isinstance(payload, dict):
            raise ProviderError(
                message="ipstack schema changed: expected object payload",
                retryable=False,
            )
        if payload.get("success") is False:
            raise ProviderError(
                message="ipstack API rejected credentials or request",
                retryable=False,
            )
        return payload

    @staticmethod
    def _validate_ip(value: str) -> str:
        try:
            return str(ipaddress.ip_address(value.strip()))
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported input for ipstack: {value}",
                retryable=False,
            ) from exc
