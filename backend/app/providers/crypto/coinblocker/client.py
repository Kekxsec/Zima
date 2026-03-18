# backend/app/providers/crypto/coinblocker/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_coinblocker.py (MIT licensed)
# Copyright (c) Steve Micallef.
import time
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class CoinBlockerProvider(BaseProviderClient):
    name = "coinblocker"
    feed_url = "https://zerodot1.gitlab.io/CoinBlockerLists/list.txt"

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
        self._cached_hosts: set[str] | None = None

    async def check_mining(
        self, *, domain: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        blacklist = self._fetch_blacklist()
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
            if host not in blacklist:
                continue

            findings.append(
                dict(
                    provider=self.name,
                    category="reputation",
                    title="Hostname listed in CoinBlocker list",
                    description=f"{host} appears in the CoinBlocker browser-cryptomining blocklist",
                    entity_type="hostname",
                    entity_value=host,
                    confidence=0.76,
                    tags=["reputation", "malicious", "coinblocker", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"CoinBlocker feed lookup for {host}",
                    raw={"host": host, "feed": self.feed_url},
                    confidence=0.76,
                )
            )
        return findings

    async def _fetch_blacklist(self) -> set[str]:
        if self._cached_hosts is not None and self._cache_expires_at > time.time():
            return self._cached_hosts

        try:
            response = await self._get(self.feed_url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="CoinBlocker feed request failed",
                retryable=True,
            ) from exc

        if response.status_code == 429:
            raise ProviderError(
                message="CoinBlocker feed rate limited request",
                retryable=True,
            )
        if response.status_code >= 500:
            raise ProviderError(
                message="CoinBlocker feed upstream unavailable",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code != 200:
            raise ProviderError(
                message="CoinBlocker feed returned unexpected response",
                retryable=False,
                status_code=response.status_code,
            )
        if not response.content.strip():
            raise ProviderError(
                message="CoinBlocker feed returned empty response body",
                retryable=False,
            )

        hosts: set[str] = set()
        for idx, raw_line in enumerate(response.content.splitlines()):
            if idx >= self._max_feed_lines:
                break
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            host = line.lower().strip(".")
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
        if entity_type in {"domain", "hostname"}:
            return value
        if entity_type == "url":
            parsed = urllib.parse.urlparse(value)
            return (parsed.hostname or "").strip().lower().strip(".")
        return ""
