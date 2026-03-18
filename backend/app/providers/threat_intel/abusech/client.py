# backend/app/providers/threat_intel/abusech/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_abusech.py (MIT licensed)
# Copyright (c) Steve Micallef.
import csv
import io
import ipaddress
import time
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class AbuseChProvider(BaseProviderClient):
    name = "abusech"
    feodo_url = "https://feodotracker.abuse.ch/downloads/ipblocklist.txt"
    ssl_url = "https://sslbl.abuse.ch/blacklist/sslipblacklist.csv"
    urlhaus_url = "https://urlhaus.abuse.ch/downloads/csv_recent/"

    def __init__(
        self,
        timeout_seconds: int = 15,
        max_feed_lines: int = 250000,
        cache_ttl_seconds: int = 21600,
        max_prefixlen: int = 24,
    ):
        self._timeout_seconds = timeout_seconds
        self._max_feed_lines = max_feed_lines
        self._cache_ttl_seconds = cache_ttl_seconds
        self._max_prefixlen = max_prefixlen
        self._cache_expires_at: dict[str, float] = {}
        self._cache_values: dict[str, set[str]] = {}

    async def check_malware(
        self,
        *,
        domain: str | None = None,
        ip_address: str | None = None,
        url: str | None = None,
    ) -> list[dict[str, Any]]:
        max_prefix = int(self._max_prefixlen)

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        if url is not None:
            _inputs.append(("url", url))

        has_ip = any(et == "ip_address" for et, _ in _inputs)
        has_host = any(et in {"domain", "hostname", "url"} for et, _ in _inputs)

        feodo = await self._fetch_feodo() if has_ip else set()
        ssl = await self._fetch_ssl() if has_ip else set()
        urlhaus = await self._fetch_urlhaus_hosts() if (has_ip or has_host) else set()

        findings: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []
        seen: set[tuple[str, str, str]] = set()

        for _entity_type, _value in _inputs:
            if _entity_type == "ip_address":
                ip_value = self._validate_ipv4(_value)
                self._append_if_hit(
                    "feodotracker",
                    ip_value,
                    {ip_value},
                    feodo,
                    findings,
                    evidence,
                    seen,
                )
                self._append_if_hit(
                    "sslbl", ip_value, {ip_value}, ssl, findings, evidence, seen
                )
                self._append_if_hit(
                    "urlhaus", ip_value, {ip_value}, urlhaus, findings, evidence, seen
                )
                continue

            if _entity_type == "netblock":
                network = self._validate_netblock(_value)
                if network.prefixlen < max_prefix:
                    continue
                ips = {str(ip) for ip in network}
                self._append_if_hit(
                    "feodotracker",
                    _value,
                    ips,
                    feodo,
                    findings,
                    evidence,
                    seen,
                    entity_type="netblock",
                )
                self._append_if_hit(
                    "sslbl",
                    _value,
                    ips,
                    ssl,
                    findings,
                    evidence,
                    seen,
                    entity_type="netblock",
                )

            host = self._extract_host(_entity_type, _value)
            if not host:
                continue
            self._append_if_hit(
                "urlhaus",
                host,
                {host},
                urlhaus,
                findings,
                evidence,
                seen,
                entity_type="hostname",
            )

        return findings

    def _append_if_hit(
        self,
        source: str,
        display_value: str,
        candidates: set[str],
        feed: set[str],
        findings: list[dict[str, Any]],
        evidence: list[dict[str, Any]],
        seen: set[tuple[str, str, str]],
        *,
        entity_type: str = "ip_address",
    ) -> None:
        match = next((candidate for candidate in candidates if candidate in feed), "")
        if not match:
            return
        dedupe = (source, entity_type, display_value)
        if dedupe in seen:
            return
        seen.add(dedupe)
        findings.append(
            dict(
                provider=self.name,
                category="reputation",
                title=f"Target listed in abuse.ch {source}",
                description=f"{display_value} matched abuse.ch {source} intelligence feed",
                entity_type=entity_type,
                entity_value=display_value,
                confidence=0.78,
                tags=["reputation", "abusech", source, "malicious", "passive"],
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description=f"abuse.ch {source} lookup for {display_value}",
                raw={"source": source, "value": display_value, "matched": match},
                confidence=0.78,
            )
        )

    async def _fetch_feodo(self) -> set[str]:
        cached = self._from_cache("feodo")
        if cached is not None:
            return cached
        response = await self._get(self.feodo_url)
        items = set()
        for idx, raw_line in enumerate(response.splitlines()):
            if idx >= self._max_feed_lines:
                break
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if self._is_valid_ipv4(line):
                items.add(line)
        if not items:
            raise ProviderError(
                message="abuse.ch Feodo tracker feed returned no usable records",
                retryable=False,
            )
        self._to_cache("feodo", items)
        return items

    async def _fetch_ssl(self) -> set[str]:
        cached = self._from_cache("ssl")
        if cached is not None:
            return cached
        response = await self._get(self.ssl_url)
        items = set()
        for idx, raw_line in enumerate(response.splitlines()):
            if idx >= self._max_feed_lines:
                break
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [part.strip() for part in line.split(",")]
            if len(parts) < 2:
                continue
            candidate = parts[1]
            if self._is_valid_ipv4(candidate):
                items.add(candidate)
        if not items:
            raise ProviderError(
                message="abuse.ch SSLBL feed returned no usable records",
                retryable=False,
            )
        self._to_cache("ssl", items)
        return items

    async def _fetch_urlhaus_hosts(self) -> set[str]:
        cached = self._from_cache("urlhaus")
        if cached is not None:
            return cached
        response = await self._get(self.urlhaus_url)
        items = set()
        reader = csv.reader(io.StringIO(response))
        for idx, row in enumerate(reader):
            if idx >= self._max_feed_lines:
                break
            if not row:
                continue
            first = row[0].strip() if row[0] else ""
            if first.startswith("#"):
                continue
            url = row[2].strip() if len(row) > 2 else ""
            if not url:
                continue
            parsed = urllib.parse.urlparse(url)
            host = (parsed.hostname or "").strip().lower().strip(".")
            if not host:
                continue
            items.add(host)
        if not items:
            raise ProviderError(
                message="abuse.ch URLhaus feed returned no usable records",
                retryable=False,
            )
        self._to_cache("urlhaus", items)
        return items

    async def _get(self, url: str) -> str:
        try:
            response = await self._get(url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="abuse.ch request failed",
                retryable=True,
            ) from exc
        if response.status_code == 429:
            raise ProviderError(
                message="abuse.ch rate limited request",
                retryable=True,
            )
        if response.status_code >= 500:
            raise ProviderError(
                message="abuse.ch upstream unavailable",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code != 200:
            raise ProviderError(
                message="abuse.ch returned unexpected response",
                retryable=False,
                status_code=response.status_code,
            )
        if not response.content.strip():
            raise ProviderError(
                message="abuse.ch returned empty response body",
                retryable=False,
            )
        return response.content

    def _from_cache(self, key: str) -> set[str] | None:
        expiry = self._cache_expires_at.get(key, 0.0)
        if expiry <= time.time():
            return None
        return self._cache_values.get(key)

    def _to_cache(self, key: str, value: set[str]) -> None:
        self._cache_values[key] = value
        self._cache_expires_at[key] = time.time() + max(self._cache_ttl_seconds, 0)

    @staticmethod
    def _extract_host(entity_type: str, raw_value: str) -> str:
        value = raw_value.strip().lower().strip(".")
        if not value:
            return ""
        if entity_type in {"domain", "hostname"}:
            return value
        if entity_type == "url":
            parsed = urllib.parse.urlparse(value)
            return (parsed.hostname or "").strip().lower().strip(".")
        return ""

    @staticmethod
    def _validate_ipv4(value: str) -> str:
        try:
            parsed = ipaddress.ip_address(value.strip())
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported input for abuse.ch provider: {value}",
                retryable=False,
            ) from exc
        if parsed.version != 4:
            raise ProviderError(
                message=f"Unsupported input for abuse.ch provider (IPv4 only): {value}",
                retryable=False,
            )
        return str(parsed)

    @staticmethod
    def _validate_netblock(value: str) -> ipaddress.IPv4Network:
        try:
            network = ipaddress.ip_network(value.strip(), strict=False)
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported netblock for abuse.ch provider: {value}",
                retryable=False,
            ) from exc
        if network.version != 4:
            raise ProviderError(
                message=f"Unsupported netblock for abuse.ch provider (IPv4 only): {value}",
                retryable=False,
            )
        return network

    @staticmethod
    def _is_valid_ipv4(value: str) -> bool:
        try:
            return ipaddress.ip_address(value).version == 4
        except ValueError:
            return False
