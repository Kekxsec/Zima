# backend/app/providers/threat_intel/voipbl/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_voipbl.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
import time
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class VoIPBLProvider(BaseProviderClient):
    name = "voipbl"
    feed_url = "https://voipbl.org/update"

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
                    title="IP listed in VoIPBL",
                    description=f"{ip_value} appears in VoIPBL feed",
                    entity_type="ip_address",
                    entity_value=ip_value,
                    confidence=0.76,
                    tags=["reputation", "voipbl", "malicious", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"VoIPBL feed lookup for {ip_value}",
                    raw={"ip": ip_value, "feed": self.feed_url},
                    confidence=0.76,
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
                message="VoIPBL feed request failed",
                retryable=True,
            ) from exc
        if response.status_code == 429:
            raise ProviderError(
                message="VoIPBL feed rate limited request",
                retryable=True,
            )
        if response.status_code >= 500:
            raise ProviderError(
                message="VoIPBL feed upstream unavailable",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code != 200:
            raise ProviderError(
                message="VoIPBL feed returned unexpected response",
                retryable=False,
                status_code=response.status_code,
            )
        if not response.content.strip():
            raise ProviderError(
                message="VoIPBL feed returned empty response body",
                retryable=False,
            )
        ips: set[str] = set()
        for idx, raw_line in enumerate(response.content.splitlines()):
            if idx >= self._max_feed_lines:
                break
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            try:
                network = ipaddress.ip_network(line, strict=False)
            except ValueError:
                continue
            if network.version != 4:
                continue
            for ip_value in network:
                ips.add(str(ip_value))
        self._cached_ips = ips
        self._cache_expires_at = time.time() + max(self._cache_ttl_seconds, 0)
        return ips

    @staticmethod
    def _validate_ipv4(value: str) -> str:
        try:
            parsed = ipaddress.ip_address(value.strip())
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported input for VoIPBL: {value}",
                retryable=False,
            ) from exc
        if parsed.version != 4:
            raise ProviderError(
                message=f"Unsupported input for VoIPBL (IPv4 only): {value}",
                retryable=False,
            )
        return str(parsed)

    def _expand_netblock(self, netblock: str) -> list[str]:
        try:
            network = ipaddress.ip_network(netblock.strip(), strict=False)
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported netblock for VoIPBL: {netblock}",
                retryable=False,
            ) from exc
        if network.version != 4:
            raise ProviderError(
                message=f"Unsupported netblock for VoIPBL (IPv4 only): {netblock}",
                retryable=False,
            )
        max_prefix = 24
        if network.prefixlen < max_prefix:
            return []
        return [str(ip) for ip in network]
