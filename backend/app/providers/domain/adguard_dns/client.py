# backend/app/providers/domain/adguard_dns/client.py
from __future__ import annotations

from typing import Any

from backend.app.providers.base.client import BaseProviderClient

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_adguard_dns.py (MIT licensed)
# Copyright (c) bcoles.
from backend.app.providers.base.utils import ResolverFunc, default_resolver


class AdGuardDNSProvider(BaseProviderClient):
    name = "adguard_dns"
    default_nameservers = ("94.140.14.14", "94.140.15.15")
    family_nameservers = ("94.140.14.15", "94.140.15.16")
    sinkhole_ip = "94.140.14.35"

    def __init__(
        self, resolver: ResolverFunc = default_resolver, timeout_seconds: float = 3.0
    ):
        self._resolver = resolver
        self._timeout_seconds = timeout_seconds

    async def resolve_dns(self, domain: str) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen_hosts = set()
        host = self._normalize_host("domain", domain)
        if not host or host in seen_hosts:
            return findings
        seen_hosts.add(host)

        family_answers = self._resolve(host, self.family_nameservers)
        default_answers = self._resolve(host, self.default_nameservers)
        if not family_answers or not default_answers:
            return findings

        family_blocked = self.sinkhole_ip in family_answers
        default_blocked = self.sinkhole_ip in default_answers
        if not family_blocked and not default_blocked:
            return findings

        profile = "family" if family_blocked else "default"
        findings.append(
            dict(
                provider=self.name,
                category="reputation",
                title="Hostname blocked by AdGuard DNS profile",
                description=f"{host} resolved to AdGuard sinkhole response via {profile} profile",
                entity_type="hostname",
                entity_value=host,
                confidence=0.67,
                tags=["reputation", "adguard_dns", "passive"],
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description=f"AdGuard DNS profile check for {host}",
                raw={
                    "host": host,
                    "family_answers": sorted(family_answers),
                    "default_answers": sorted(default_answers),
                },
                confidence=0.67,
            )
        )

        return findings

    def _resolve(self, host: str, nameservers: tuple[str, ...]) -> set[str]:
        return {
            answer.strip().lower()
            for answer in self._resolver(host, nameservers, self._timeout_seconds)
            if answer.strip()
        }

    @staticmethod
    def _normalize_host(entity_type: str, value: str) -> str:
        if entity_type not in {"domain", "hostname"}:
            return ""
        return value.strip().lower().strip(".")
