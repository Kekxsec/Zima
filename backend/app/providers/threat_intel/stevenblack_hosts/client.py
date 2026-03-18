# backend/app/providers/threat_intel/stevenblack_hosts/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_stevenblack_hosts.py (MIT licensed)
# Copyright (c) bcoles.
import time
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class StevenBlackHostsProvider(BaseProviderClient):
    name = "stevenblack_hosts"
    feed_url = "https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts"

    def __init__(
        self,
        timeout_seconds: int = 15,
        max_feed_lines: int = 500000,
        cache_ttl_seconds: int = 86400,
    ):
        self._timeout_seconds = timeout_seconds
        self._max_feed_lines = max_feed_lines
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cache_expires_at = 0.0
        self._cached_hosts: set[str] | None = None

    async def get_threat_feed(
        self, *, domain: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        blocklist = self._fetch_feed()
        findings = []
        evidence = []
        seen = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if url is not None:
            _inputs.append(("url", url))
        for _entity_type, _value in _inputs:
            host = self._extract_target(_entity_type, _value)
            if not host or host in seen:
                continue
            seen.add(host)
            if host not in blocklist:
                continue
            findings.append(
                dict(
                    provider=self.name,
                    category="reputation",
                    title="Hostname listed in Steven Black hosts feed",
                    description=f"{host} appears in Steven Black Hosts consolidated block list",
                    entity_type="hostname",
                    entity_value=host,
                    confidence=0.76,
                    tags=["reputation", "stevenblack_hosts", "malicious", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"Steven Black Hosts lookup for {host}",
                    raw={"host": host, "feed": self.feed_url},
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
                message="Steven Black Hosts feed request failed",
                retryable=True,
            ) from exc
        if response.status_code == 429:
            raise ProviderError(
                message="Steven Black Hosts feed rate limited request",
                retryable=True,
            )
        if response.status_code >= 500:
            raise ProviderError(
                message="Steven Black Hosts feed upstream unavailable",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code != 200:
            raise ProviderError(
                message="Steven Black Hosts feed returned unexpected response",
                retryable=False,
                status_code=response.status_code,
            )
        if not response.content.strip():
            raise ProviderError(
                message="Steven Black Hosts feed returned empty response body",
                retryable=False,
            )
        hosts: set[str] = set()
        for idx, raw_line in enumerate(response.content.splitlines()):
            if idx >= self._max_feed_lines:
                break
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            host = parts[1].strip().lower().strip(".")
            if not host or host in {"localhost", "localhost.localdomain"}:
                continue
            hosts.add(host)
        self._cached_hosts = hosts
        self._cache_expires_at = time.time() + max(self._cache_ttl_seconds, 0)
        return hosts

    @staticmethod
    def _extract_target(entity_type: str, value: str) -> str:
        raw = value.strip().lower().strip(".")
        if not raw:
            return ""
        if entity_type in {"domain", "hostname"}:
            return raw
        if entity_type == "url":
            parsed = urllib.parse.urlparse(raw)
            return (parsed.hostname or "").strip().lower().strip(".")
        return ""
