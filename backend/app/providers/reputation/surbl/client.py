# backend/app/providers/reputation/surbl/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_surbl.py (MIT licensed)
# Copyright (c) bcoles.
import ipaddress
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)
from backend.app.providers.base.utils import ResolverFunc, default_resolver


class SURBLProvider(BaseProviderClient):
    name = "surbl"
    dns_zone = "multi.surbl.org"

    def __init__(
        self,
        resolver: ResolverFunc = default_resolver,
        timeout_seconds: float = 3.0,
        max_prefixlen: int = 24,
    ):
        self._resolver = resolver
        self._timeout_seconds = timeout_seconds
        self._max_prefixlen = max_prefixlen

    async def check_dnsbl(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen_targets = set()

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            targets = self._targets_for_entity(_entity_type, _value)
            for target, target_type in targets:
                if not target or (target_type, target) in seen_targets:
                    continue
                seen_targets.add((target_type, target))
                answers = self._query(target, target_type == "ip_address")
                if not answers:
                    continue
                matched = sorted(
                    {answer for answer in answers if answer.startswith("127.0.0.")}
                )
                if not matched:
                    continue
                if "127.0.0.1" in matched:
                    raise ProviderError(
                        message="SURBL rejected lookup request",
                        retryable=False,
                    )
                findings.append(
                    dict(
                        provider=self.name,
                        category="reputation",
                        title="Target listed in SURBL",
                        description=f"{target} matched SURBL DNSBL responses: {', '.join(matched)}",
                        entity_type=target_type,
                        entity_value=target,
                        confidence=0.76,
                        tags=["reputation", "surbl", "malicious", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"SURBL DNSBL lookup for {target}",
                        raw={"target": target, "answers": matched},
                        confidence=0.76,
                    )
                )
        return findings

    def _targets_for_entity(
        self, entity_type: str, value: str
    ) -> list[tuple[str, str]]:
        if entity_type == "ip_address":
            return [(self._validate_ipv4(value), "ip_address")]
        if entity_type == "netblock":
            ips = self._expand_netblock(value)
            return [(ip_value, "ip_address") for ip_value in ips]
        if entity_type in {"domain", "hostname"}:
            target = value.strip().lower().strip(".")
            if target:
                return [(target, "hostname")]
        return []

    def _query(self, target: str, is_ip: bool) -> list[str]:
        if is_ip:
            lookup = f"{'.'.join(reversed(target.split('.')))}.{self.dns_zone}"
        else:
            lookup = f"{target}.{self.dns_zone}"
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
                message=f"Unsupported netblock for SURBL: {netblock}",
                retryable=False,
            ) from exc
        if network.version != 4:
            raise ProviderError(
                message=f"Unsupported netblock for SURBL (IPv4 only): {netblock}",
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
                message=f"Unsupported input for SURBL: {value}",
                retryable=False,
            ) from exc
        if parsed.version != 4:
            raise ProviderError(
                message=f"Unsupported input for SURBL (IPv4 only): {value}",
                retryable=False,
            )
        return str(parsed)
