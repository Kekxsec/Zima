# backend/app/providers/reputation/greynoise_community/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity = FindingSeverity.HIGH if classification in {"malicious", "attack"} else FindingSeverity.MEDIUM
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_greynoise_community.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
from datetime import date, datetime
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class GreyNoiseCommunityProvider(BaseProviderClient):
    name = "greynoise_community"
    base_url = "https://api.greynoise.io/v3/community"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_reputation(self, ip_address: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="GreyNoise Community API key is required",
                retryable=False,
            )
        age_limit_days = 30
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
        if payload.get("noise") is not True:
            return findings
        if age_limit_days > 0 and not self._within_age_limit(
            payload.get("last_seen"), age_limit_days
        ):
            return findings
        classification = (
            str(payload.get("classification", "")).strip().lower() or "unknown"
        )

        findings.append(
            dict(
                provider=self.name,
                category="reputation",
                title="IP flagged by GreyNoise Community",
                description=f"{ip_value} classified by GreyNoise as {classification}",
                entity_type="ip_address",
                entity_value=ip_value,
                confidence=0.78 if classification in {"malicious", "attack"} else 0.7,
                tags=["reputation", "greynoise", "passive", "scanner_intel"],
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description=f"GreyNoise Community lookup for {ip_value}",
                raw=payload,
                confidence=0.78 if classification in {"malicious", "attack"} else 0.7,
            )
        )
        return findings

    async def _query(self, ip_value: str, api_key: str) -> dict:
        url = f"{self.base_url}/{ip_value}"
        headers = {"key": api_key}
        payload = await self._get(
            url,
            label="GreyNoiseCommunity",
            headers=headers,
            timeout=self._timeout_seconds,
        )
        if not isinstance(payload, dict):
            raise ProviderError(
                message="GreyNoise Community schema changed: expected object payload",
                retryable=False,
            )
        return payload

    @staticmethod
    def _validate_ip(value: str) -> str:
        try:
            return str(ipaddress.ip_address(value.strip()))
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported input for GreyNoise Community: {value}",
                retryable=False,
            ) from exc

    @staticmethod
    def _within_age_limit(last_seen: str | None, age_limit_days: int) -> bool:
        if not last_seen:
            return False
        try:
            last_seen_date = datetime.strptime(last_seen, "%Y-%m-%d").date()
        except ValueError:
            return False
        age_days = (date.today() - last_seen_date).days
        return age_days <= age_limit_days
