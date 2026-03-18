# backend/app/providers/reputation/spamhaus/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_spamhaus.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)
from backend.app.providers.base.utils import ResolverFunc, default_resolver


class SpamhausProvider(BaseProviderClient):
    name = "spamhaus"
    dns_zone = "zen.spamhaus.org"
    checks = {
        "127.0.0.2": "Spammer",
        "127.0.0.3": "Spammer",
        "127.0.0.4": "Proxies/Trojans",
        "127.0.0.5": "Proxies/Trojans",
        "127.0.0.6": "Proxies/Trojans",
        "127.0.0.7": "Proxies/Trojans",
        "127.0.0.10": "Potential spammer",
        "127.0.0.11": "Potential spammer",
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
                if answer == "127.255.255.252":
                    continue
                if answer in {"127.255.255.254", "127.255.255.255"}:
                    raise ProviderError(
                        message="Spamhaus query denied or query limit exceeded",
                        retryable=True,
                    )
                reason = self.checks.get(answer)
                if not reason:
                    continue
                findings.append(
                    dict(
                        provider=self.name,
                        category="reputation",
                        title="IP listed in Spamhaus ZEN",
                        description=f"{ip_value} matched Spamhaus response {answer}: {reason}",
                        entity_type="ip_address",
                        entity_value=ip_value,
                        confidence=0.78,
                        tags=["reputation", "spamhaus", "malicious", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Spamhaus ZEN DNSBL lookup for {ip_value}",
                        raw={"ip": ip_value, "answer": answer, "reason": reason},
                        confidence=0.78,
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
                message=f"Unsupported netblock for Spamhaus: {netblock}",
                retryable=False,
            ) from exc
        if network.version != 4:
            raise ProviderError(
                message=f"Unsupported netblock for Spamhaus (IPv4 only): {netblock}",
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
                message=f"Unsupported input for Spamhaus: {value}",
                retryable=False,
            ) from exc
        if parsed.version != 4:
            raise ProviderError(
                message=f"Unsupported input for Spamhaus (IPv4 only): {value}",
                retryable=False,
            )
        return str(parsed)
