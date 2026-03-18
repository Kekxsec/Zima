# backend/app/providers/threat_intel/botvrij/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_botvrij.py (MIT licensed)
# Copyright (c) Steve Micallef.
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class BotvrijProvider(BaseProviderClient):
    name = "botvrij"
    feed_url = "https://www.botvrij.eu/data/blocklist/blocklist_full.csv"

    def __init__(self, timeout_seconds: int = 15, max_feed_lines: int = 250000):
        self._timeout_seconds = timeout_seconds
        self._max_feed_lines = max_feed_lines

    async def get_threat_feed(
        self, *, domain: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        blacklist = self._fetch_blacklist()
        findings = []
        evidence = []

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if url is not None:
            _inputs.append(("url", url))
        for _entity_type, _value in _inputs:
            target = self._extract_target(_entity_type, _value)
            if not target:
                continue
            if target not in blacklist:
                continue

            findings.append(
                dict(
                    provider=self.name,
                    category="reputation",
                    title="Hostname listed in Botvrij blocklist",
                    description=f"{target} is present in the Botvrij domain blocklist feed",
                    entity_type="hostname",
                    entity_value=target,
                    confidence=0.72,
                    tags=["reputation", "botvrij", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"Botvrij blocklist lookup for {target}",
                    raw={"target": target, "feed": self.feed_url},
                    confidence=0.72,
                )
            )

        return findings

    async def _fetch_blacklist(self) -> set[str]:
        try:
            response = await self._get(self.feed_url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="Botvrij blocklist request failed",
                retryable=True,
            ) from exc

        if response.status_code == 429:
            raise ProviderError(
                message="Botvrij blocklist rate limited request",
                retryable=True,
            )
        if response.status_code >= 500:
            raise ProviderError(
                message="Botvrij blocklist upstream unavailable",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code != 200:
            raise ProviderError(
                message="Botvrij blocklist returned unexpected response",
                retryable=False,
                status_code=response.status_code,
            )
        if not response.content.strip():
            raise ProviderError(
                message="Botvrij blocklist returned empty response body",
                retryable=False,
            )

        hosts: set[str] = set()
        for idx, raw_line in enumerate(response.content.splitlines()):
            if idx >= self._max_feed_lines:
                break
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            host = line.split(",", 1)[0].strip().lower().strip(".")
            if not host:
                continue
            hosts.add(host)
        return hosts

    @staticmethod
    def _extract_target(entity_type: str, raw_value: str) -> str:
        value = raw_value.strip().lower().strip(".")
        if not value:
            return ""
        if entity_type == "url":
            parsed = urllib.parse.urlparse(value)
            host = (parsed.hostname or "").strip().lower().strip(".")
            return host
        if entity_type in {"domain", "hostname"}:
            return value
        return ""
