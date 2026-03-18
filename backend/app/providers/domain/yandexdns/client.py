# backend/app/providers/domain/yandexdns/client.py
from __future__ import annotations

from typing import Any

from backend.app.providers.base.client import BaseProviderClient

# Extracted/adapted from SpiderFoot module: modules/sfp_yandexdns.py (MIT licensed)
# Copyright (c) Steve Micallef.
from backend.app.providers.base.utils import ResolverFunc, default_resolver


class YandexDNSProvider(BaseProviderClient):
    name = "yandexdns"
    nameservers = ("77.88.8.7", "77.88.8.3")
    checks = {
        "213.180.193.250": (
            "Yandex infected-site blocklist match",
            "removed_severity",
            True,
        ),
        "93.158.134.250": (
            "Yandex adult-content blocklist match",
            "removed_severity",
            False,
        ),
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
        tags = ["reputation", "yandex_dns", "passive"]
        if is_malicious:
            tags = ["reputation", "malicious", "yandex_dns", "passive"]

        findings.append(
            dict(
                provider=self.name,
                category="reputation",
                title="Hostname matched Yandex DNS blocklist response",
                description=f"{host} resolved to Yandex policy response {matched_ip}: {description}",
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
                description=f"Yandex DNS resolver check for {host}",
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
