# backend/app/providers/reputation/ipregistry/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_ipregistry.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class IPRegistryProvider(BaseProviderClient):
    name = "ipregistry"
    base_url = "https://api.ipregistry.co"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_reputation(self, ip_address: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="ipregistry API key is required",
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
        location = payload.get("location")
        if isinstance(location, dict):
            country = (
                (location.get("country") or {}).get("name", "")
                if isinstance(location.get("country"), dict)
                else ""
            )
            region = (
                (location.get("region") or {}).get("name", "")
                if isinstance(location.get("region"), dict)
                else ""
            )
            city = str(location.get("city", "")).strip()
            postal = str(location.get("postal", "")).strip()
            location_str = ", ".join(
                part for part in [city, region, postal, str(country).strip()] if part
            )
            if location_str:
                findings.append(
                    dict(
                        provider=self.name,
                        category="infrastructure_intel",
                        title="IP geolocation enrichment from ipregistry",
                        description=f"ipregistry geolocated {ip_value} to {location_str}",
                        entity_type="ip_address",
                        entity_value=ip_value,
                        confidence=0.68,
                        tags=["geoip", "ipregistry", "passive"],
                    )
                )
        security = payload.get("security")
        if isinstance(security, dict):
            malicious = any(
                bool(security.get(k)) for k in ("is_abuser", "is_attacker", "is_threat")
            )
            if malicious:
                findings.append(
                    dict(
                        provider=self.name,
                        category="reputation",
                        title="IP flagged by ipregistry security signals",
                        description=f"{ip_value} marked as potentially abusive/threatening by ipregistry",
                        entity_type="ip_address",
                        entity_value=ip_value,
                        confidence=0.76,
                        tags=["reputation", "ipregistry", "malicious", "passive"],
                    )
                )
        evidence.append(
            dict(
                source=self.name,
                description=f"ipregistry lookup for {ip_value}",
                raw=payload,
                confidence=0.68,
            )
        )
        return findings

    async def _query(self, ip_value: str, api_key: str) -> dict:
        query = urllib.parse.urlencode({"key": api_key})
        url = f"{self.base_url}/{ip_value}?{query}"
        payload = await self._get(
            url, label="IPRegistry", timeout=self._timeout_seconds
        )
        if not isinstance(payload, dict):
            raise ProviderError(
                message="ipregistry schema changed: expected object payload",
                retryable=False,
            )
        return payload

    @staticmethod
    def _validate_ip(value: str) -> str:
        try:
            return str(ipaddress.ip_address(value.strip()))
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported input for ipregistry: {value}",
                retryable=False,
            ) from exc
