# backend/app/providers/domain/dns_for_family/client.py
from __future__ import annotations

from typing import Any

from backend.app.providers.base.client import BaseProviderClient

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_dns_for_family.py (MIT licensed)
# Copyright (c) bcoles.
from backend.app.providers.base.utils import ResolverFunc, default_resolver


class DNSForFamilyProvider(BaseProviderClient):
    name = "dns_for_family"
    nameservers = ("94.130.180.225", "78.47.64.161")
    sinkhole_ip = "159.69.10.249"

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

        answers = self._resolve(host, self.nameservers)
        if self.sinkhole_ip not in answers:
            return findings

        findings.append(
            dict(
                provider=self.name,
                category="reputation",
                title="Hostname blocked by DNS for Family",
                description=f"{host} resolved to DNS for Family sinkhole response",
                entity_type="hostname",
                entity_value=host,
                confidence=0.66,
                tags=["reputation", "dns_for_family", "passive"],
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description=f"DNS for Family resolver check for {host}",
                raw={"host": host, "answers": sorted(answers)},
                confidence=0.66,
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
