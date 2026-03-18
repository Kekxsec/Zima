# backend/app/providers/reputation/blocklistde/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_blocklistde.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class BlocklistDEProvider(BaseProviderClient):
    name = "blocklistde"
    feed_url = "https://lists.blocklist.de/lists/all.txt"

    def __init__(self, timeout_seconds: int = 15, max_feed_lines: int = 250000):
        self._timeout_seconds = timeout_seconds
        self._max_feed_lines = max_feed_lines

    async def get_reputation(self, ip_address: str) -> list[dict[str, Any]]:
        blacklist = self._fetch_blacklist()
        findings = []
        evidence = []

        ip_value = ip_address.strip()
        if not ip_value:
            return findings
        if not self._is_valid_ip(ip_value):
            raise ProviderError(
                message=f"Unsupported input for blocklist.de feed: {ip_value}",
                retryable=False,
            )

        if ip_value not in blacklist:
            return findings

        findings.append(
            dict(
                provider=self.name,
                category="reputation",
                title="IP listed in blocklist.de feed",
                description=f"{ip_value} is present in the blocklist.de all.txt feed",
                entity_type="ip_address",
                entity_value=ip_value,
                confidence=0.72,
                tags=["reputation", "blocklistde", "passive"],
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description=f"blocklist.de feed lookup for {ip_value}",
                raw={"ipAddress": ip_value, "feed": self.feed_url},
                confidence=0.72,
            )
        )

        return findings

    async def _fetch_blacklist(self) -> set[str]:
        try:
            response = await self._get(self.feed_url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="blocklist.de feed request failed",
                retryable=True,
            ) from exc

        if response.status_code == 429:
            raise ProviderError(
                message="blocklist.de feed rate limited request",
                retryable=True,
            )
        if response.status_code >= 500:
            raise ProviderError(
                message="blocklist.de feed upstream unavailable",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code != 200:
            raise ProviderError(
                message="blocklist.de feed returned unexpected response",
                retryable=False,
                status_code=response.status_code,
            )
        if not response.content.strip():
            raise ProviderError(
                message="blocklist.de feed returned empty response body",
                retryable=False,
            )

        ips: set[str] = set()
        for idx, raw_line in enumerate(response.content.splitlines()):
            if idx >= self._max_feed_lines:
                break
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if not self._is_valid_ip(line):
                continue
            ips.add(line)
        return ips

    @staticmethod
    def _is_valid_ip(value: str) -> bool:
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False
