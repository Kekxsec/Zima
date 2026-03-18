# backend/app/providers/domain/cloudflaredns/client.py
from __future__ import annotations

from typing import Any

from backend.app.providers.base.client import BaseProviderClient

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity = FindingSeverity.HIGH
# STRIPPED: severity = FindingSeverity.MEDIUM
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_cloudflaredns.py (MIT licensed)
# Copyright (c) Steve Micallef.
from backend.app.providers.base.utils import ResolverFunc, default_resolver


class CloudflareDNSProvider(BaseProviderClient):
    name = "cloudflaredns"
    family_nameservers = ("1.1.1.3", "1.0.0.3")
    malware_nameservers = ("1.1.1.2", "1.0.0.2")

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
        malware_answers = self._resolve(host, self.malware_nameservers)
        if not family_answers and not malware_answers:
            return findings

        family_blocked = "0.0.0.0" in family_answers
        malware_blocked = "0.0.0.0" in malware_answers
        if not family_blocked and not malware_blocked:
            return findings

        if malware_blocked:
            return findings

            title = "Hostname blocked by Cloudflare malware DNS"
            profile = "malware"
            confidence = 0.74
            tags = ["reputation", "malicious", "cloudflare_dns", "passive"]
        else:
            title = "Hostname blocked by Cloudflare family DNS"
            profile = "family"
            confidence = 0.68
            tags = ["reputation", "cloudflare_dns", "passive"]

        findings.append(
            dict(
                provider=self.name,
                category="reputation",
                title=title,
                description=f"{host} resolved to sinkhole response on Cloudflare {profile} DNS profile",
                entity_type="hostname",
                entity_value=host,
                confidence=confidence,
                tags=tags,
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description=f"Cloudflare DNS profile check for {host}",
                raw={
                    "host": host,
                    "family_answers": sorted(family_answers),
                    "malware_answers": sorted(malware_answers),
                },
                confidence=confidence,
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
