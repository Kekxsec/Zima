# backend/app/providers/ip/torexits/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_torexits.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
import time
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class TorExitsProvider(BaseProviderClient):
    name = "torexits"
    feed_url = "https://onionoo.torproject.org/details?search=flag:exit"

    def __init__(
        self,
        timeout_seconds: int = 15,
        cache_ttl_seconds: int = 3600,
    ):
        self._timeout_seconds = timeout_seconds
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cache_expires_at = 0.0
        self._cached_ips: set[str] | None = None

    async def check_tor_exit(self, ip_address: str) -> list[dict[str, Any]]:
        exit_ips = self._fetch_feed()
        findings = []
        evidence = []
        seen = set()
        targets = [self._normalize_ip(ip_address)]
        for ip_value in targets:
            if not ip_value or ip_value in seen:
                continue
            seen.add(ip_value)
            if ip_value not in exit_ips:
                continue
            findings.append(
                dict(
                    provider=self.name,
                    category="infrastructure_intel",
                    title="IP is a Tor exit node",
                    description=f"{ip_value} appears in Tor Project exit relay list",
                    entity_type="ip_address",
                    entity_value=ip_value,
                    confidence=0.8,
                    tags=["tor", "exit_node", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"Tor exit list lookup for {ip_value}",
                    raw={"ip": ip_value, "feed": self.feed_url},
                    confidence=0.8,
                )
            )
        return findings

    async def _fetch_feed(self) -> set[str]:
        if self._cached_ips is not None and self._cache_expires_at > time.time():
            return self._cached_ips
        payload = await self._get(
            self.feed_url, label="TorExits", timeout=self._timeout_seconds
        )
        relays = payload.get("relays")
        if not isinstance(relays, list):
            raise ProviderError(
                message="Tor exit list schema changed: expected relays list",
                retryable=False,
            )
        ips: set[str] = set()
        for relay in relays:
            if not isinstance(relay, dict):
                continue
            for value in relay.get("or_addresses", []) or []:
                normalized = self._normalize_relay_address(value)
                if normalized:
                    ips.add(normalized)
            for value in relay.get("exit_addresses", []) or []:
                normalized = self._normalize_relay_address(value)
                if normalized:
                    ips.add(normalized)
        self._cached_ips = ips
        self._cache_expires_at = time.time() + max(self._cache_ttl_seconds, 0)
        return ips

    @staticmethod
    def _normalize_relay_address(value: str) -> str:
        raw = str(value).strip()
        if not raw:
            return ""
        if raw.startswith("[") and "]" in raw:
            raw = raw[1:].split("]", 1)[0]
        elif ":" in raw and raw.count(":") == 1 and "." in raw:
            raw = raw.split(":", 1)[0]
        try:
            return str(ipaddress.ip_address(raw))
        except ValueError:
            return ""

    @staticmethod
    def _normalize_ip(value: str) -> str:
        try:
            return str(ipaddress.ip_address(value.strip()))
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported input for Tor exits: {value}",
                retryable=False,
            ) from exc

    def _expand_netblock(self, netblock: str) -> list[str]:
        try:
            network = ipaddress.ip_network(netblock.strip(), strict=False)
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported netblock for Tor exits: {netblock}",
                retryable=False,
            ) from exc
        max_prefix = int(24 if network.version == 4 else 120)
        if network.prefixlen < max_prefix:
            return []
        return [str(ip) for ip in network]
