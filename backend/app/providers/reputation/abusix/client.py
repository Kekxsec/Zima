# backend/app/providers/reputation/abusix/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity = FindingSeverity.LOW if reason == "white" else FindingSeverity.HIGH
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_abusix.py (MIT licensed)
# Copyright (c) bcoles.
import ipaddress
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)
from backend.app.providers.base.utils import ResolverFunc, default_resolver


class AbusixProvider(BaseProviderClient):
    name = "abusix"
    dns_zone = "combined.mail.abusix.zone"
    checks = {
        "127.0.0.2": "black",
        "127.0.0.3": "black (composite/heuristic)",
        "127.0.0.4": "exploit / authbl",
        "127.0.0.5": "forged",
        "127.0.0.6": "backscatter",
        "127.0.0.11": "policy (generic rDNS)",
        "127.0.0.12": "policy (missing rDNS)",
        "127.0.0.100": "noip",
        "127.0.1.1": "dblack",
        "127.0.1.2": "dblack (newly observed domain)",
        "127.0.1.3": "dblack (unshortened)",
        "127.0.2.1": "white",
        "127.0.3.1": "shorthash",
        "127.0.3.2": "diskhash",
        "127.0.4.1": "btc-wallets",
        "127.0.5.1": "attachhash",
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

    async def check_dnsbl(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="Abusix API key is required",
                retryable=False,
            )

        findings = []
        evidence = []
        seen = set()
        max_prefix = int(self._max_prefixlen)

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type == "ip_address":
                targets = [self._validate_ip(_value)]
                entity_type = "ip_address"
                display_value = targets[0]
            elif _entity_type == "netblock":
                network = self._validate_netblock(_value)
                if network.prefixlen < max_prefix:
                    continue
                targets = [str(ip) for ip in network]
                entity_type = "netblock"
                display_value = _value
            elif _entity_type in {"domain", "hostname"}:
                domain = self._normalize_host(_value)
                if not domain:
                    raise ProviderError(
                        message=f"Unsupported input for Abusix: {_value}",
                        retryable=False,
                    )
                targets = [domain]
                entity_type = "hostname"
                display_value = domain
            else:
                continue

            for target in targets:
                if (entity_type, target) in seen:
                    continue
                seen.add((entity_type, target))
                answers = self._query(target, api_key)
                for answer in answers:
                    reason = self.checks.get(answer)
                    if not reason:
                        continue

                    findings.append(
                        dict(
                            provider=self.name,
                            category="reputation",
                            title="Target listed in Abusix Mail Intelligence",
                            description=f"{display_value} matched Abusix response {answer}: {reason}",
                            entity_type=entity_type,
                            entity_value=display_value,
                            confidence=0.74,
                            tags=["reputation", "abusix", "passive", "dnsbl"],
                        )
                    )
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"Abusix lookup for {target}",
                            raw={
                                "target": target,
                                "response": answer,
                                "reason": reason,
                            },
                            confidence=0.74,
                        )
                    )
                    break

        return findings

    def _query(self, target: str, api_key: str) -> list[str]:
        lookup = self._build_lookup(target, api_key)
        try:
            return [
                answer.strip().lower()
                for answer in self._resolver(lookup, (), self._timeout_seconds)
                if answer.strip()
            ]
        except Exception as exc:
            raise ProviderError(
                message="Abusix DNS query failed",
                retryable=True,
            ) from exc

    def _build_lookup(self, target: str, api_key: str) -> str:
        try:
            ip = ipaddress.ip_address(target)
            return f"{ip.reverse_pointer.rsplit('.', 2)[0]}.{api_key}.{self.dns_zone}"
        except ValueError:
            pass
        return f"{target}.{api_key}.{self.dns_zone}"

    @staticmethod
    def _validate_ip(value: str) -> str:
        try:
            return str(ipaddress.ip_address(value.strip()))
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported input for Abusix: {value}",
                retryable=False,
            ) from exc

    @staticmethod
    def _validate_netblock(value: str) -> ipaddress.IPv4Network | ipaddress.IPv6Network:
        try:
            return ipaddress.ip_network(value.strip(), strict=False)
        except ValueError as exc:
            raise ProviderError(
                message=f"Unsupported netblock for Abusix: {value}",
                retryable=False,
            ) from exc

    @staticmethod
    def _normalize_host(value: str) -> str:
        host = value.strip().lower().strip(".")
        if not host or "." not in host:
            return ""
        return host
