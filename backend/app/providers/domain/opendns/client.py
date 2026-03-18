# backend/app/providers/domain/opendns/client.py
from __future__ import annotations

from typing import Any

from backend.app.providers.base.client import BaseProviderClient

# Extracted/adapted from SpiderFoot module: modules/sfp_opendns.py (MIT licensed)
# Copyright (c) Steve Micallef.
from backend.app.providers.base.utils import ResolverFunc, default_resolver


class OpenDNSProvider(BaseProviderClient):
    name = "opendns"
    nameservers = ("208.67.222.123", "208.67.220.123")
    checks = {
        "146.112.61.105": ("OpenDNS botnet blocklist match", "removed_severity", True),
        "146.112.61.106": (
            "OpenDNS adult-content blocklist match",
            "removed_severity",
            False,
        ),
        "146.112.61.107": ("OpenDNS malware blocklist match", "removed_severity", True),
        "146.112.61.108": (
            "OpenDNS phishing blocklist match",
            "removed_severity",
            True,
        ),
        "146.112.61.109": ("OpenDNS policy blocklist match", "removed_severity", False),
        "146.112.61.110": ("OpenDNS malware blocklist match", "removed_severity", True),
    }

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
        if not answers:
            return findings

        matched_ip = ""
        matched_meta = None
        for answer in sorted(answers):
            if answer in self.checks:
                matched_ip = answer
                matched_meta = self.checks[answer]
                break
        if not matched_meta:
            return findings

        description, severity, is_malicious = matched_meta
        tags = ["reputation", "opendns", "passive"]
        if is_malicious:
            tags = ["reputation", "malicious", "opendns", "passive"]

        findings.append(
            dict(
                provider=self.name,
                category="reputation",
                title="Hostname matched OpenDNS blocklist response",
                description=f"{host} resolved to OpenDNS policy response {matched_ip}: {description}",
                severity=severity,
                entity_type="hostname",
                entity_value=host,
                confidence=0.74 if is_malicious else 0.67,
                tags=tags,
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description=f"OpenDNS resolver check for {host}",
                raw={
                    "host": host,
                    "matched_ip": matched_ip,
                    "answers": sorted(answers),
                },
                confidence=0.74 if is_malicious else 0.67,
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
