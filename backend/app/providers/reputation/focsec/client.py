# backend/app/providers/reputation/focsec/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# STRIPPED: severity=FindingSeverity.MEDIUM
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_focsec.py (MIT licensed)
# Copyright (c) bcoles.
import ipaddress
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class FocsecProvider(BaseProviderClient):
    name = "focsec"
    base_url = "https://api.focsec.com/v1/ip"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_reputation(self, ip_address: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="Focsec API key is required",
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
        if payload.get("is_bot") is True:
            findings.append(
                dict(
                    provider=self.name,
                    category="reputation",
                    title="IP flagged as bot by Focsec",
                    description=f"Focsec marked {ip_value} as bot-associated",
                    entity_type="ip_address",
                    entity_value=ip_value,
                    confidence=0.78,
                    tags=["reputation", "focsec", "malicious", "passive"],
                )
            )
        if (
            payload.get("is_proxy") is True
            or payload.get("is_vpn") is True
            or payload.get("is_tor") is True
        ):
            transport = []
            if payload.get("is_proxy"):
                transport.append("proxy")
            if payload.get("is_vpn"):
                transport.append("vpn")
            if payload.get("is_tor"):
                transport.append("tor")
            findings.append(
                dict(
                    provider=self.name,
                    category="infrastructure_intel",
                    title="IP anonymization infrastructure detected",
                    description=f"Focsec marked {ip_value} as {'/'.join(transport)} infrastructure",
                    entity_type="ip_address",
                    entity_value=ip_value,
                    confidence=0.72,
                    tags=["infrastructure", "focsec", "passive"] + transport,
                )
            )
        location = ", ".join(
            filter(
                None,
                [
                    str(payload.get("city", "")).strip(),
                    str(payload.get("country", "")).strip(),
                ],
            )
        )
        if location:
            findings.append(
                dict(
                    provider=self.name,
                    category="infrastructure_intel",
                    title="IP geolocation enrichment from Focsec",
                    description=f"Focsec geolocated {ip_value} to {location}",
                    entity_type="ip_address",
                    entity_value=ip_value,
                    confidence=0.67,
                    tags=["geoip", "focsec", "passive"],
                )
            )
        evidence.append(
            dict(
                source=self.name,
                description=f"Focsec lookup for {ip_value}",
                raw=payload,
                confidence=0.72,
            )
        )
        return findings

    async def _query(self, ip_value: str, api_key: str) -> dict:
        query = urllib.parse.urlencode({"api_key": api_key})
        url = f"{self.base_url}/{ip_value}?{query}"
        payload = await self._get(url, label="Focsec", timeout=self._timeout_seconds)
        if not isinstance(payload, dict):
            raise ProviderError(
                message="Focsec schema changed: expected object payload",
                retryable=False,
            )
        return payload

    @staticmethod
    def _validate_ip(value: str) -> str:
        try:
            return str(ipaddress.ip_address(value.strip()))
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported input for Focsec: {value}",
                retryable=False,
            ) from exc
