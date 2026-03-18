# backend/app/providers/reputation/sorbs/client.py
from __future__ import annotations

# Extracted/adapted from SpiderFoot module: modules/sfp_sorbs.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)
from backend.app.providers.base.utils import ResolverFunc, default_resolver


class SORBSProvider(BaseProviderClient):
    name = "sorbs"
    dns_zone = "dnsbl.sorbs.net"
    checks = {
        "127.0.0.2": ("Open HTTP proxy", "removed_severity", "proxy"),
        "127.0.0.3": ("Open SOCKS proxy", "removed_severity", "proxy"),
        "127.0.0.4": ("Open proxy", "removed_severity", "proxy"),
        "127.0.0.5": ("Open SMTP relay", "removed_severity", "malicious"),
        "127.0.0.6": ("Spammer", "removed_severity", "malicious"),
        "127.0.0.7": (
            "Vulnerability exposed to spammers",
            "removed_severity",
            "malicious",
        ),
        "127.0.0.8": ("Host ignored by SORBS", "removed_severity", "neutral"),
        "127.0.0.9": ("Hijacked host", "removed_severity", "malicious"),
        "127.0.0.10": ("Dynamic IP range", "removed_severity", "neutral"),
        "127.0.0.11": ("Misconfigured A/MX", "removed_severity", "suspicious"),
        "127.0.0.12": ("Host does not send mail", "removed_severity", "neutral"),
        "127.0.0.14": (
            "Network does not contain servers",
            "removed_severity",
            "neutral",
        ),
    }

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
            answers = self._query_dnsbl(ip_value)
            if not answers:
                continue
            for answer in answers:
                meta = self.checks.get(answer)
                if not meta:
                    continue
                reason, severity, kind = meta
                tags = ["reputation", "sorbs", "passive", kind]
                if kind in {"malicious", "proxy"}:
                    tags.append("malicious")
                findings.append(
                    dict(
                        provider=self.name,
                        category="reputation",
                        title="IP listed in SORBS",
                        description=f"{ip_value} matched SORBS response {answer}: {reason}",
                        severity=severity,
                        entity_type="ip_address",
                        entity_value=ip_value,
                        confidence=0.76 if severity in {"removed_severity"} else 0.62,
                        tags=tags,
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"SORBS DNSBL lookup for {ip_value}",
                        raw={"ip": ip_value, "answer": answer, "reason": reason},
                        confidence=0.76 if severity in {"removed_severity"} else 0.62,
                    )
                )
        return findings

    def _query_dnsbl(self, ip_value: str) -> list[str]:
        lookup = f"{'.'.join(reversed(ip_value.split('.')))}.{self.dns_zone}"
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
                message=f"Unsupported netblock for SORBS: {netblock}",
                retryable=False,
            ) from exc
        if network.version != 4:
            raise ProviderError(
                message=f"Unsupported netblock for SORBS (IPv4 only): {netblock}",
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
                message=f"Unsupported input for SORBS: {value}",
                retryable=False,
            ) from exc
        if parsed.version != 4:
            raise ProviderError(
                message=f"Unsupported input for SORBS (IPv4 only): {value}",
                retryable=False,
            )
        return str(parsed)
