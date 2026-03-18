# backend/app/providers/threat_intel/threatfox/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_threatfox.py (MIT licensed)
# Copyright (c) bcoles.
import ipaddress
import json
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ThreatFoxProvider(BaseProviderClient):
    name = "threatfox"
    api_url = "https://threatfox-api.abuse.ch/api/v1/"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def get_threat_feed(self, ip_address: str) -> list[dict[str, Any]]:
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
        findings.append(
            dict(
                provider=self.name,
                category="reputation",
                title="IP listed in ThreatFox IOC feed",
                description=f"{ip_value} returned IOC records from ThreatFox search API",
                entity_type="ip_address",
                entity_value=ip_value,
                confidence=0.79,
                tags=["reputation", "threatfox", "malicious", "passive"],
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description=f"ThreatFox IOC lookup for {ip_value}",
                raw={"ip": ip_value, "records": payload[:3]},
                confidence=0.79,
            )
        )
        return findings

    async def _query(self, ip_value: str) -> list[dict]:
        body = json.dumps({"query": "search_ioc", "search_term": ip_value})
        headers = {"Accept": "application/json"}
        payload = await self._post(
            self.api_url,
            data=body,
            label="ThreatFox",
            headers=headers,
            timeout=self._timeout_seconds,
        )
        if not isinstance(payload, dict):
            raise ProviderError(
                message="ThreatFox schema changed: expected object response",
                retryable=False,
            )
        status = str(payload.get("query_status", "")).lower()
        if status == "no_result":
            return []
        if status != "ok":
            raise ProviderError(
                message=f"ThreatFox query failed with status: {status or 'unknown'}",
                retryable=False,
            )
        data = payload.get("data")
        if not isinstance(data, list):
            raise ProviderError(
                message="ThreatFox schema changed: expected data list",
                retryable=False,
            )
        return [row for row in data if isinstance(row, dict)]

    @staticmethod
    def _validate_ip(value: str) -> str:
        try:
            return str(ipaddress.ip_address(value.strip()))
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported input for ThreatFox: {value}",
                retryable=False,
            ) from exc
