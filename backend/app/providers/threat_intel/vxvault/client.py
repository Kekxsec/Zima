# backend/app/providers/threat_intel/vxvault/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_vxvault.py (MIT licensed)
# Copyright (c) Steve Micallef.
import time
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class VxVaultProvider(BaseProviderClient):
    name = "vxvault"
    feed_url = "http://vxvault.net/URL_List.php"

    def __init__(
        self,
        timeout_seconds: int = 15,
        max_feed_lines: int = 200000,
        cache_ttl_seconds: int = 64800,
    ):
        self._timeout_seconds = timeout_seconds
        self._max_feed_lines = max_feed_lines
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cache_expires_at = 0.0
        self._cached_hosts: set[str] | None = None

    async def check_malware(
        self,
        *,
        domain: str | None = None,
        ip_address: str | None = None,
        url: str | None = None,
    ) -> list[dict[str, Any]]:
        blacklist = self._fetch_feed()
        findings = []
        evidence = []
        seen = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        if url is not None:
            _inputs.append(("url", url))
        for _entity_type, _value in _inputs:
            target = self._extract_target(_entity_type, _value)
            if not target or target in seen:
                continue
            seen.add(target)
            if target not in blacklist:
                continue
            findings.append(
                dict(
                    provider=self.name,
                    category="reputation",
                    title="Target listed in VXVault malware feed",
                    description=f"{target} appears in VXVault malicious URL feed",
                    entity_type="ip_address"
                    if self._looks_like_ip(target)
                    else "hostname",
                    entity_value=target,
                    confidence=0.76,
                    tags=["reputation", "vxvault", "malicious", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"VXVault feed lookup for {target}",
                    raw={"target": target, "feed": self.feed_url},
                    confidence=0.76,
                )
            )
        return findings

    async def _fetch_feed(self) -> set[str]:
        if self._cached_hosts is not None and self._cache_expires_at > time.time():
            return self._cached_hosts
        try:
            response = await self._get(self.feed_url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="VXVault feed request failed",
                retryable=True,
            ) from exc
        if response.status_code == 429:
            raise ProviderError(
                message="VXVault feed rate limited request",
                retryable=True,
            )
        if response.status_code >= 500:
            raise ProviderError(
                message="VXVault feed upstream unavailable",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code != 200:
            raise ProviderError(
                message="VXVault feed returned unexpected response",
                retryable=False,
                status_code=response.status_code,
            )
        if not response.content.strip():
            raise ProviderError(
                message="VXVault feed returned empty response body",
                retryable=False,
            )
        hosts: set[str] = set()
        for idx, raw_line in enumerate(response.content.splitlines()):
            if idx >= self._max_feed_lines:
                break
            line = raw_line.strip().lower()
            if not line.startswith("http"):
                continue
            parsed = urllib.parse.urlparse(line)
            host = (parsed.hostname or "").strip().lower().strip(".")
            if not host:
                continue
            hosts.add(host)
        self._cached_hosts = hosts
        self._cache_expires_at = time.time() + max(self._cache_ttl_seconds, 0)
        return hosts

    @staticmethod
    def _extract_target(entity_type: str, raw_value: str) -> str:
        value = raw_value.strip().lower().strip(".")
        if not value:
            return ""
        if entity_type in {"domain", "hostname", "ip_address"}:
            return value
        if entity_type == "url":
            parsed = urllib.parse.urlparse(value)
            return (parsed.hostname or "").strip().lower().strip(".")
        return ""

    @staticmethod
    def _looks_like_ip(value: str) -> bool:
        parts = value.split(".")
        if len(parts) != 4:
            return False
        for part in parts:
            if not part.isdigit():
                return False
            num = int(part)
            if num < 0 or num > 255:
                return False
        return True
