# backend/app/providers/threat_intel/openphish/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_openphish.py (MIT licensed)
# Copyright (c) Steve Micallef.
from urllib.parse import urlparse

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class OpenPhishProvider(BaseProviderClient):
    name = "openphish"
    feed_url = "https://www.openphish.com/feed.txt"

    def __init__(self, timeout_seconds: int = 10):
        self._timeout_seconds = timeout_seconds

    async def check_phishing(
        self, *, domain: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        try:
            response = await self._get(self.feed_url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="OpenPhish request failed",
                retryable=True,
            ) from exc
        if response.status_code == 429:
            raise ProviderError(
                message="OpenPhish rate limited request",
                retryable=True,
            )
        if response.status_code >= 500:
            raise ProviderError(
                message="OpenPhish upstream unavailable",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code != 200:
            raise ProviderError(
                message="OpenPhish returned unexpected response",
                status_code=response.status_code,
            )

        malicious_hosts = self.parse_blacklist(response.content)
        findings = []
        evidence = []

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if url is not None:
            _inputs.append(("url", url))
        for _entity_type, _value in _inputs:
            host = self._entity_to_host(_entity_type, _value)
            if not host:
                continue
            if host not in malicious_hosts:
                continue

            findings.append(
                dict(
                    provider=self.name,
                    category="phishing_intel",
                    title="Known phishing host",
                    description=f"{host} appears in OpenPhish feed",
                    entity_type="hostname",
                    entity_value=host,
                    confidence=0.8,
                    tags=["phishing", "reputation", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"OpenPhish feed match for {host}",
                    raw={"feed_url": self.feed_url, "host": host},
                    confidence=0.8,
                )
            )

        return findings

    @staticmethod
    def _entity_to_host(entity_type: str, value: str) -> str:
        normalized = value.strip().lower()
        if entity_type in {"domain", "hostname"}:
            return normalized
        if entity_type == "url":
            parsed = urlparse(normalized)
            if parsed.hostname:
                return parsed.hostname.lower()
            return ""
        return ""

    @staticmethod
    def parse_blacklist(blacklist: str) -> set[str]:
        hosts = set()
        for line in blacklist.splitlines():
            if not line or not line.startswith("http"):
                continue
            url = line.strip().lower()
            parts = url.split("/")
            if len(parts) < 3:
                continue
            host = parts[2]
            if ":" in host:
                host = host.split(":", 1)[0]
            if "." not in host:
                continue
            hosts.add(host)
        return hosts
