# backend/app/providers/ip/ipapico/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_ipapico.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class IPApiCoProvider(BaseProviderClient):
    name = "ipapico"
    base_url = "https://ipapi.co"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def get_geolocation(self, ip_address: str) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen = set()
        ip_value = self._validate_ip(ip_address)
        if ip_value in seen:
            return findings
        seen.add(ip_value)
        payload = await self._query(ip_value)
        if not payload:
            return findings
        country = str(payload.get("country", "")).strip()
        if not country:
            return findings
        location_parts = [
            str(payload.get("city", "")).strip(),
            str(payload.get("region", "")).strip(),
            str(payload.get("region_code", "")).strip(),
            str(payload.get("country_name", "")).strip(),
            country,
        ]
        location = ", ".join(part for part in location_parts if part)
        findings.append(
            dict(
                provider=self.name,
                category="infrastructure_intel",
                title="IP geolocation enrichment from ipapi.co",
                description=f"ipapi.co geolocated {ip_value} to {location}",
                entity_type="ip_address",
                entity_value=ip_value,
                confidence=0.68,
                tags=["geoip", "ipapico", "passive"],
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description=f"ipapi.co lookup for {ip_value}",
                raw=payload,
                confidence=0.68,
            )
        )
        return findings

    async def _query(self, ip_value: str) -> dict:
        url = f"{self.base_url}/{ip_value}/json/"
        payload = await self._get(url, label="IPApiCo", timeout=self._timeout_seconds)
        if not isinstance(payload, dict):
            raise ProviderError(
                message="ipapi.co schema changed: expected object payload",
                retryable=False,
            )
        return payload

    @staticmethod
    def _validate_ip(value: str) -> str:
        try:
            return str(ipaddress.ip_address(value.strip()))
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported input for ipapi.co: {value}",
                retryable=False,
            ) from exc
