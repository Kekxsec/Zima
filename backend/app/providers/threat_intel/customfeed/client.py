# backend/app/providers/threat_intel/customfeed/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_customfeed.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
import time
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class CustomFeedProvider(BaseProviderClient):
    name = "customfeed"

    def __init__(
        self,
        url: str = "",
        timeout_seconds: int = 15,
        cache_ttl_seconds: int = 0,
        max_feed_lines: int = 500000,
    ):
        self._url = url
        self._timeout_seconds = timeout_seconds
        self._cache_ttl_seconds = cache_ttl_seconds
        self._max_feed_lines = max_feed_lines
        self._cache_expires_at = 0.0
        self._cache_lines: list[str] | None = None

    async def get_threat_feed(
        self,
        *,
        asn: str | None = None,
        domain: str | None = None,
        ip_address: str | None = None,
    ) -> list[dict[str, Any]]:
        url = str(self._url).strip()
        if not url:
            raise ProviderError(
                message="Custom feed URL is required",
                retryable=False,
            )
        lines = self._fetch_lines(url)
        findings = []
        evidence = []
        seen = set()
        _inputs: list[tuple[str, str]] = []
        if asn is not None:
            _inputs.append(("asn", asn))
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            matched = self._match_entity(_entity_type, _value, lines)
            if not matched:
                continue
            key = (_entity_type, _value)
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                dict(
                    provider=self.name,
                    category="reputation",
                    title="Target listed in custom threat feed",
                    description=f"{_value} matched an entry in configured custom feed",
                    entity_type=_entity_type,
                    entity_value=_value,
                    confidence=0.78,
                    tags=["reputation", "customfeed", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"Custom feed match for {_value}",
                    raw={"value": _value, "matched": matched, "feed_url": url},
                    confidence=0.78,
                )
            )
        return findings

    async def _fetch_lines(self, url: str) -> list[str]:
        if self._cache_lines is not None and self._cache_expires_at > time.time():
            return self._cache_lines
        try:
            response = await self._get(url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="Custom feed request failed",
                retryable=True,
            ) from exc
        if response.status_code == 429:
            raise ProviderError(
                message="Custom feed request rate limited",
                retryable=True,
            )
        if response.status_code >= 500:
            raise ProviderError(
                message="Custom feed upstream unavailable",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code != 200:
            raise ProviderError(
                message="Custom feed returned unexpected response",
                retryable=False,
                status_code=response.status_code,
            )
        if not response.content.strip():
            raise ProviderError(
                message="Custom feed returned empty response body",
                retryable=False,
            )
        lines = []
        for idx, raw_line in enumerate(response.content.splitlines()):
            if idx >= self._max_feed_lines:
                break
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            lines.append(line)
        self._cache_lines = lines
        self._cache_expires_at = time.time() + max(self._cache_ttl_seconds, 0)
        return lines

    def _match_entity(self, entity_type: str, raw_value: str, lines: list[str]) -> str:
        value = raw_value.strip()
        if not value:
            return ""
        if entity_type == "ip_address":
            return self._match_ip(value, lines)
        if entity_type == "netblock":
            return self._match_netblock(value, lines)
        if entity_type in {"domain", "hostname"}:
            host = value.lower().strip(".")
            base = self._base_domain(host)
            for line in lines:
                candidate = line.lower().strip(".")
                if candidate == host or (base and candidate == base):
                    return line
            return ""
        if entity_type == "bgp_asn":
            normalized = value.upper().replace("AS", "")
            for line in lines:
                candidate = line.upper().replace("AS", "")
                if candidate == normalized:
                    return line
            return ""
        return ""

    @staticmethod
    def _match_ip(value: str, lines: list[str]) -> str:
        try:
            target = ipaddress.ip_address(value)
        except ValueError:
            return ""
        for line in lines:
            candidate = line.strip()
            try:
                if "/" in candidate:
                    if target in ipaddress.ip_network(candidate, strict=False):
                        return line
                elif target == ipaddress.ip_address(candidate):
                    return line
            except ValueError:
                continue
        return ""

    @staticmethod
    def _match_netblock(value: str, lines: list[str]) -> str:
        try:
            target = ipaddress.ip_network(value, strict=False)
        except ValueError:
            return ""
        for line in lines:
            candidate = line.strip()
            try:
                if "/" in candidate:
                    candidate_net = ipaddress.ip_network(candidate, strict=False)
                    if target.overlaps(candidate_net):
                        return line
                else:
                    if ipaddress.ip_address(candidate) in target:
                        return line
            except ValueError:
                continue
        return ""

    @staticmethod
    def _base_domain(host: str) -> str:
        parts = [part for part in host.split(".") if part]
        if len(parts) < 2:
            return host
        return ".".join(parts[-2:])
