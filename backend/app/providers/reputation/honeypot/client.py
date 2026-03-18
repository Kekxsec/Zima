# backend/app/providers/reputation/honeypot/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity = FindingSeverity.HIGH if threat_level >= 40 else FindingSeverity.MEDIUM
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_honeypot.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)
from backend.app.providers.base.utils import ResolverFunc, default_resolver


class HoneyPotProvider(BaseProviderClient):
    name = "honeypot"
    dns_zone = "dnsbl.httpbl.org"
    statuses = {
        0: "Search Engine",
        1: "Suspicious",
        2: "Harvester",
        3: "Suspicious & Harvester",
        4: "Comment Spammer",
        5: "Suspicious & Comment Spammer",
        6: "Harvester & Comment Spammer",
        7: "Suspicious & Harvester & Comment Spammer",
    }

    def __init__(
        self,
        resolver: ResolverFunc = default_resolver,
        api_key: str = "",
        timeout_seconds: float = 3.0,
        max_prefixlen: int = 24,
    ):
        self._resolver = resolver
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._max_prefixlen = max_prefixlen

    async def check_dnsbl(self, ip_address: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="Project Honey Pot API key is required",
                retryable=False,
            )
        try:
            threatscore_min = 0
            timelimit_days = 30
        except (TypeError, ValueError) as exc:
            raise ProviderError(
                message="Invalid honeypot option: threatscore_min and timelimit_days must be integers",
                retryable=False,
            ) from exc
        include_searchengine = False

        findings = []
        evidence = []
        seen = set()
        ips = [self._validate_ipv4(ip_address)]
        for ip_value in ips:
            if not ip_value or ip_value in seen:
                continue
            seen.add(ip_value)
            answers = self._query(ip_value, api_key)
            if not answers:
                continue
            parsed = self._parse_answers(
                answers, threatscore_min, timelimit_days, include_searchengine
            )
            if not parsed:
                continue
            days_since, threat_level, status_code, status_label = parsed

            findings.append(
                dict(
                    provider=self.name,
                    category="reputation",
                    title="IP listed in Project Honey Pot",
                    description=f"{ip_value} matched Project Honey Pot status '{status_label}', threat {threat_level}, last seen {days_since} days",
                    entity_type="ip_address",
                    entity_value=ip_value,
                    confidence=0.78,
                    tags=["reputation", "honeypot", "passive", "malicious"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"Project Honey Pot DNSBL lookup for {ip_value}",
                    raw={
                        "ip": ip_value,
                        "days_since": days_since,
                        "threat_level": threat_level,
                        "status_code": status_code,
                        "status_label": status_label,
                    },
                    confidence=0.78,
                )
            )
        return findings

    def _query(self, ip_value: str, api_key: str) -> list[str]:
        lookup = f"{api_key}.{'.'.join(reversed(ip_value.split('.')))}.{self.dns_zone}"
        return [
            answer.strip().lower()
            for answer in self._resolver(lookup, (), self._timeout_seconds)
            if answer.strip()
        ]

    def _parse_answers(
        self,
        answers: list[str],
        threatscore_min: int,
        timelimit_days: int,
        include_searchengine: bool,
    ):
        for answer in answers:
            parts = answer.split(".")
            if len(parts) != 4 or parts[0] != "127":
                continue
            try:
                days_since = int(parts[1])
                threat_level = int(parts[2])
                status_code = int(parts[3])
            except ValueError:
                continue
            if days_since > timelimit_days:
                continue
            if threat_level < threatscore_min:
                continue
            if status_code == 0 and not include_searchengine:
                continue
            status_label = self.statuses.get(status_code, f"Unknown ({status_code})")
            return days_since, threat_level, status_code, status_label
        return None

    @staticmethod
    def _validate_ipv4(value: str) -> str:
        try:
            parsed = ipaddress.ip_address(value.strip())
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported input for Project Honey Pot: {value}",
                retryable=False,
            ) from exc
        if parsed.version != 4:
            raise ProviderError(
                message=f"Unsupported input for Project Honey Pot (IPv4 only): {value}",
                retryable=False,
            )
        return str(parsed)

    def _expand_netblock(self, netblock: str) -> list[str]:
        try:
            network = ipaddress.ip_network(netblock.strip(), strict=False)
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported netblock for Project Honey Pot: {netblock}",
                retryable=False,
            ) from exc
        if network.version != 4:
            raise ProviderError(
                message=f"Unsupported netblock for Project Honey Pot (IPv4 only): {netblock}",
                retryable=False,
            )
        max_prefix = max(int(self._max_prefixlen), 24)
        if network.prefixlen < max_prefix:
            return []
        return [str(ip) for ip in network]
