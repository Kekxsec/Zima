# backend/app/providers/threat_intel/emergingthreats/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_emergingthreats.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
import time
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class EmergingThreatsProvider(BaseProviderClient):
    name = "emergingthreats"
    feed_url = "https://rules.emergingthreats.net/blockrules/compromised-ips.txt"

    def __init__(
        self,
        timeout_seconds: int = 15,
        max_feed_lines: int = 250000,
        cache_ttl_seconds: int = 21600,
    ):
        self._timeout_seconds = timeout_seconds
        self._max_feed_lines = max_feed_lines
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cache_expires_at = 0.0
        self._cached_ips: set[str] | None = None

    async def get_threat_feed(self, ip_address: str) -> list[dict[str, Any]]:
        listed_ips = self._fetch_feed()
        findings = []
        evidence = []
        seen = set()
        targets = [self._validate_ipv4(ip_address)]
        for ip_value in targets:
            if not ip_value or ip_value in seen:
                continue
            seen.add(ip_value)
            if ip_value not in listed_ips:
                continue
            findings.append(
                dict(
                    provider=self.name,
                    category="reputation",
                    title="IP listed in Emerging Threats feed",
                    description=f"{ip_value} appears in the Emerging Threats compromised IP feed",
                    entity_type="ip_address",
                    entity_value=ip_value,
                    confidence=0.78,
                    tags=["reputation", "emergingthreats", "malicious", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"Emerging Threats feed lookup for {ip_value}",
                    raw={"ip": ip_value, "feed": self.feed_url},
                    confidence=0.78,
                )
            )
        return findings

    async def _fetch_feed(self) -> set[str]:
        if self._cached_ips is not None and self._cache_expires_at > time.time():
            return self._cached_ips
        try:
            response = await self._get(self.feed_url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="Emerging Threats feed request failed",
                retryable=True,
            ) from exc
        if response.status_code == 429:
            raise ProviderError(
                message="Emerging Threats feed rate limited request",
                retryable=True,
            )
        if response.status_code >= 500:
            raise ProviderError(
                message="Emerging Threats feed upstream unavailable",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code != 200:
            raise ProviderError(
                message="Emerging Threats feed returned unexpected response",
                retryable=False,
                status_code=response.status_code,
            )
        if not response.content.strip():
            raise ProviderError(
                message="Emerging Threats feed returned empty response body",
                retryable=False,
            )
        ips: set[str] = set()
        for idx, raw_line in enumerate(response.content.splitlines()):
            if idx >= self._max_feed_lines:
                break
            line = raw_line.strip()
            if not line:
                continue
            try:
                parsed = ipaddress.ip_address(line)
            except ValueError:
                continue
            if parsed.version != 4:
                continue
            ips.add(str(parsed))
        self._cached_ips = ips
        self._cache_expires_at = time.time() + max(self._cache_ttl_seconds, 0)
        return ips

    @staticmethod
    def _validate_ipv4(value: str) -> str:
        try:
            parsed = ipaddress.ip_address(value.strip())
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported input for Emerging Threats: {value}",
                retryable=False,
            ) from exc
        if parsed.version != 4:
            raise ProviderError(
                message=f"Unsupported input for Emerging Threats (IPv4 only): {value}",
                retryable=False,
            )
        return str(parsed)

    def _expand_netblock(self, netblock: str) -> list[str]:
        try:
            network = ipaddress.ip_network(netblock.strip(), strict=False)
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported netblock for Emerging Threats: {netblock}",
                retryable=False,
            ) from exc
        if network.version != 4:
            raise ProviderError(
                message=f"Unsupported netblock for Emerging Threats (IPv4 only): {netblock}",
                retryable=False,
            )
        max_prefix = 24
        if network.prefixlen < max_prefix:
            return []
        return [str(ip) for ip in network]
