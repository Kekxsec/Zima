# backend/app/providers/reputation/abuseipdb/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM if score < 95 else FindingSeverity.HIGH
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_abuseipdb.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class AbuseIPDBProvider(BaseProviderClient):
    name = "abuseipdb"
    base_url = "https://api.abuseipdb.com/api/v2/check"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_reputation(self, ip_address: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="AbuseIPDB API key is required",
                retryable=False,
            )

        confidence_minimum = 90
        confidence_minimum = max(1, min(confidence_minimum, 100))
        max_age_days = 30
        max_age_days = max(1, min(max_age_days, 365))

        findings = []
        evidence = []
        headers = {
            "Accept": "application/json",
            "Key": api_key,
        }

        ip_value = ip_address.strip()
        if not ip_value:
            return findings
        if not self._is_valid_ip(ip_value):
            raise ProviderError(
                message=f"Unsupported input for AbuseIPDB: {ip_value}",
                retryable=False,
            )

        payload = await self._query_ip(ip_value, max_age_days, headers)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ProviderError(
                message="AbuseIPDB schema changed: expected data object",
                retryable=False,
            )

        score = data.get("abuseConfidenceScore")
        if not isinstance(score, int):
            raise ProviderError(
                message="AbuseIPDB schema changed: missing abuseConfidenceScore",
                retryable=False,
            )

        total_reports = data.get("totalReports", 0)
        if not isinstance(total_reports, int):
            total_reports = 0

        if score < confidence_minimum:
            return findings

        findings.append(
            dict(
                provider=self.name,
                category="reputation",
                title="Abusive IP reported by AbuseIPDB",
                description=f"{ip_value} exceeded abuse confidence threshold ({score} >= {confidence_minimum})",
                entity_type="ip_address",
                entity_value=ip_value,
                confidence=min(1.0, max(0.5, score / 100.0)),
                tags=["reputation", "abuseipdb", "passive"],
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description=f"AbuseIPDB check response for {ip_value}",
                raw={
                    "ipAddress": ip_value,
                    "abuseConfidenceScore": score,
                    "totalReports": total_reports,
                    "lastReportedAt": data.get("lastReportedAt"),
                },
                confidence=min(1.0, max(0.5, score / 100.0)),
            )
        )

        return findings

    async def _query_ip(
        self, ip_value: str, max_age_days: int, headers: dict[str, str]
    ) -> dict:
        params = urllib.parse.urlencode(
            {"ipAddress": ip_value, "maxAgeInDays": str(max_age_days)}
        )
        url = f"{self.base_url}?{params}"
        try:
            response = await self._get(
                url, headers=headers, timeout=self._timeout_seconds
            )
        except Exception as exc:
            raise ProviderError(
                message="AbuseIPDB request failed",
                retryable=True,
            ) from exc
        self._check_status_errors(response, "AbuseIPDB")
        payload = self._parse_json(response, "AbuseIPDB")
        if not isinstance(payload, dict):
            raise ProviderError(
                message="AbuseIPDB schema changed: expected object payload",
                retryable=False,
            )
        return payload

    @staticmethod
    def _is_valid_ip(value: str) -> bool:
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False
