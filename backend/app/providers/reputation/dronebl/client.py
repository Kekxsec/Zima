# backend/app/providers/reputation/dronebl/client.py
from __future__ import annotations

# Extracted/adapted from SpiderFoot module: modules/sfp_dronebl.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)
from backend.app.providers.base.utils import ResolverFunc, default_resolver


class DroneBLProvider(BaseProviderClient):
    name = "dronebl"
    dns_zone = "dnsbl.dronebl.org"
    checks = {
        "127.0.0.3": ("IRC drone", "removed_severity", "malicious"),
        "127.0.0.5": ("Bottler", "removed_severity", "malicious"),
        "127.0.0.6": ("Unknown spambot or drone", "removed_severity", "malicious"),
        "127.0.0.7": ("DDoS drone", "removed_severity", "malicious"),
        "127.0.0.8": ("SOCKS proxy", "removed_severity", "proxy"),
        "127.0.0.9": ("HTTP proxy", "removed_severity", "proxy"),
        "127.0.0.10": ("Proxy chain", "removed_severity", "proxy"),
        "127.0.0.11": ("Web page proxy", "removed_severity", "proxy"),
        "127.0.0.12": ("Open DNS resolver", "removed_severity", "suspicious"),
        "127.0.0.13": ("Brute-force attacker", "removed_severity", "malicious"),
        "127.0.0.14": ("Open Wingate proxy", "removed_severity", "proxy"),
        "127.0.0.15": ("Compromised router/gateway", "removed_severity", "malicious"),
        "127.0.0.16": ("Autorooting worm", "removed_severity", "malicious"),
        "127.0.0.17": ("Botnet IP (experimental)", "removed_severity", "malicious"),
        "127.0.0.18": ("Possibly compromised DNS/MX", "removed_severity", "malicious"),
        "127.0.0.19": ("Abused VPN service", "removed_severity", "vpn"),
        "127.0.0.255": ("Unknown listing", "removed_severity", "suspicious"),
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
                tags = ["reputation", "dronebl", "passive", kind]
                if kind in {"malicious", "vpn", "proxy"}:
                    tags.append("malicious")
                findings.append(
                    dict(
                        provider=self.name,
                        category="reputation",
                        title="IP listed in DroneBL",
                        description=f"{ip_value} matched DroneBL response {answer}: {reason}",
                        severity=severity,
                        entity_type="ip_address",
                        entity_value=ip_value,
                        confidence=0.76 if severity == "removed_severity" else 0.68,
                        tags=tags,
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"DroneBL DNSBL lookup for {ip_value}",
                        raw={"ip": ip_value, "answer": answer, "reason": reason},
                        confidence=0.76 if severity == "removed_severity" else 0.68,
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
                message=f"Unsupported netblock for DroneBL: {netblock}",
                retryable=False,
            ) from exc
        if network.version != 4:
            raise ProviderError(
                message=f"Unsupported netblock for DroneBL (IPv4 only): {netblock}",
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
                message=f"Unsupported input for DroneBL: {value}",
                retryable=False,
            ) from exc
        if parsed.version != 4:
            raise ProviderError(
                message=f"Unsupported input for DroneBL (IPv4 only): {value}",
                retryable=False,
            )
        return str(parsed)
