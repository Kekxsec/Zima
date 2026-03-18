# backend/app/providers/threat_intel/phishstats/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_phishstats.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class PhishStatsProvider(BaseProviderClient):
    name = "phishstats"
    api_url = "https://phishstats.info:2096/api/phishing"

    def __init__(self, timeout_seconds: int = 15, max_prefixlen: int = 24):
        self._timeout_seconds = timeout_seconds
        self._max_prefixlen = max_prefixlen

    async def check_phishing(self, ip_address: str) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen = set()
        ips = [self._validate_ip(ip_address)]
        for ip_value in ips:
            if not ip_value or ip_value in seen:
                continue
            seen.add(ip_value)
            data = await self._query(ip_value)
            if not data:
                continue
            first = data[0] if isinstance(data[0], dict) else {}
            matched_ip = str(first.get("ip", "")).strip()
            if matched_ip and matched_ip != ip_value:
                continue
            findings.append(
                dict(
                    provider=self.name,
                    category="phishing_intel",
                    title="IP listed in PhishStats feed",
                    description=f"{ip_value} returned records from PhishStats phishing API",
                    entity_type="ip_address",
                    entity_value=ip_value,
                    confidence=0.79,
                    tags=["phishing", "reputation", "phishstats", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"PhishStats lookup for {ip_value}",
                    raw={"ip": ip_value, "records": data[:3]},
                    confidence=0.79,
                )
            )
        return findings

    async def _query(self, ip_value: str) -> list[dict]:
        params = urllib.parse.urlencode({"_where": f"(ip,eq,{ip_value})", "_size": 1})
        url = f"{self.api_url}?{params}"
        headers = {"Accept": "application/json"}
        payload = await self._get(
            url, label="PhishStats", headers=headers, timeout=self._timeout_seconds
        )
        if not isinstance(payload, list):
            raise ProviderError(
                message="PhishStats schema changed: expected list response",
                retryable=False,
            )
        return [row for row in payload if isinstance(row, dict)]

    @staticmethod
    def _validate_ip(value: str) -> str:
        try:
            return str(ipaddress.ip_address(value.strip()))
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported input for PhishStats: {value}",
                retryable=False,
            ) from exc

    def _expand_netblock(self, netblock: str) -> list[str]:
        try:
            network = ipaddress.ip_network(netblock.strip(), strict=False)
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported netblock for PhishStats: {netblock}",
                retryable=False,
            ) from exc
        max_prefix = int(self._max_prefixlen)
        if network.prefixlen < max_prefix:
            return []
        return [str(ip) for ip in network]
