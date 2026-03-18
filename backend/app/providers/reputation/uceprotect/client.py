# backend/app/providers/reputation/uceprotect/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_uceprotect.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)
from backend.app.providers.base.utils import ResolverFunc, default_resolver


class UCEPROTECTProvider(BaseProviderClient):
    name = "uceprotect"
    level1_zone = "dnsbl-1.uceprotect.net"
    level2_zone = "dnsbl-2.uceprotect.net"

    def __init__(
        self,
        resolver: ResolverFunc = default_resolver,
        timeout_seconds: float = 3.0,
        max_prefixlen: int = 24,
    ):
        self._resolver = resolver
        self._timeout_seconds = timeout_seconds
        self._max_prefixlen = max_prefixlen

    async def check_dnsbl(self, ip_address: str) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen_ips = set()
        ips = [self._validate_ipv4(ip_address)]
        for ip_value in ips:
            if not ip_value or ip_value in seen_ips:
                continue
            seen_ips.add(ip_value)
            level1 = self._query_level(ip_value, self.level1_zone)
            level2 = self._query_level(ip_value, self.level2_zone)
            if not level1 and not level2:
                continue

            if level1:
                findings.append(
                    dict(
                        provider=self.name,
                        category="reputation",
                        title="IP listed in UCEPROTECT Level 1",
                        description=f"{ip_value} resolved in UCEPROTECT level 1 DNSBL",
                        entity_type="ip_address",
                        entity_value=ip_value,
                        confidence=0.79,
                        tags=[
                            "reputation",
                            "uceprotect",
                            "malicious",
                            "passive",
                            "level1",
                        ],
                    )
                )
            if level2:
                findings.append(
                    dict(
                        provider=self.name,
                        category="reputation",
                        title="IP listed in UCEPROTECT Level 2",
                        description=f"{ip_value} resolved in UCEPROTECT level 2 DNSBL",
                        entity_type="ip_address",
                        entity_value=ip_value,
                        confidence=0.7,
                        tags=["reputation", "uceprotect", "passive", "level2"],
                    )
                )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"UCEPROTECT DNSBL lookup for {ip_value}",
                    raw={
                        "ip": ip_value,
                        "level1": bool(level1),
                        "level2": bool(level2),
                    },
                    confidence=0.79 if level1 else 0.7,
                )
            )
        return findings

    def _query_level(self, ip_value: str, zone: str) -> list[str]:
        lookup = f"{'.'.join(reversed(ip_value.split('.')))}.{zone}"
        return [
            answer.strip().lower()
            for answer in self._resolver(lookup, (), self._timeout_seconds)
            if answer.strip()
        ]

    def _expand_netblock(self, netblock: str) -> list[str]:
        try:
            network = ipaddress.ip_network(netblock.strip(), strict=False)
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported netblock for UCEPROTECT: {netblock}",
                retryable=False,
            ) from exc
        if network.version != 4:
            raise ProviderError(
                message=f"Unsupported netblock for UCEPROTECT (IPv4 only): {netblock}",
                retryable=False,
            )
        max_prefix = int(self._max_prefixlen)
        if network.prefixlen < max_prefix:
            return []
        return [str(ip) for ip in network]

    @staticmethod
    def _validate_ipv4(value: str) -> str:
        try:
            parsed = ipaddress.ip_address(value.strip())
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported input for UCEPROTECT: {value}",
                retryable=False,
            ) from exc
        if parsed.version != 4:
            raise ProviderError(
                message=f"Unsupported input for UCEPROTECT (IPv4 only): {value}",
                retryable=False,
            )
        return str(parsed)
