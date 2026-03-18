# backend/app/providers/domain/cleanbrowsing/client.py
from __future__ import annotations

from typing import Any

from backend.app.providers.base.client import BaseProviderClient

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity = FindingSeverity.LOW
# STRIPPED: severity = FindingSeverity.HIGH
# STRIPPED: severity = FindingSeverity.MEDIUM
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_cleanbrowsing.py (MIT licensed)
# Copyright (c) Steve Micallef.
from backend.app.providers.base.utils import ResolverFunc, default_resolver


class CleanBrowsingProvider(BaseProviderClient):
    name = "cleanbrowsing"
    family_nameservers = ("185.228.168.168", "185.228.168.169")
    adult_nameservers = ("185.228.168.10", "185.228.169.11")
    security_nameservers = ("185.228.168.9", "185.228.169.9")

    def __init__(
        self,
        resolver: ResolverFunc = default_resolver,
        timeout_seconds: float = 3.0,
        require_public_resolution: bool = True,
    ):
        self._resolver = resolver
        self._timeout_seconds = timeout_seconds
        self._require_public_resolution = require_public_resolution

    async def resolve_dns(self, domain: str) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen_hosts = set()
        host = self._normalize_host("domain", domain)
        if not host or host in seen_hosts:
            return findings
        seen_hosts.add(host)

        if self._require_public_resolution and not self._publicly_resolves(host):
            return findings

        family = bool(self._resolve(host, self.family_nameservers))
        adult = bool(self._resolve(host, self.adult_nameservers))
        security = bool(self._resolve(host, self.security_nameservers))
        if family and adult and security:
            return findings

        blocked_profile = "family"

        tags = ["reputation", "cleanbrowsing", "passive"]
        if not security:
            blocked_profile = "security"

            tags = ["reputation", "malicious", "cleanbrowsing", "passive"]
        elif not adult:
            blocked_profile = "adult"

        findings.append(
            dict(
                provider=self.name,
                category="reputation",
                title="Hostname blocked by CleanBrowsing DNS profile",
                description=f"{host} appears blocked by CleanBrowsing {blocked_profile} profile",
                entity_type="hostname",
                entity_value=host,
                confidence=0.72 if blocked_profile == "security" else 0.65,
                tags=tags,
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description=f"CleanBrowsing profile DNS check for {host}",
                raw={
                    "host": host,
                    "family_resolves": family,
                    "adult_resolves": adult,
                    "security_resolves": security,
                },
                confidence=0.72 if blocked_profile == "security" else 0.65,
            )
        )

        return findings

    def _publicly_resolves(self, host: str) -> bool:
        return bool(self._resolve(host, ()))

    def _resolve(self, host: str, nameservers: tuple[str, ...]) -> list[str]:
        return [
            answer.strip().lower()
            for answer in self._resolver(host, nameservers, self._timeout_seconds)
            if answer.strip()
        ]

    @staticmethod
    def _normalize_host(entity_type: str, value: str) -> str:
        if entity_type not in {"domain", "hostname"}:
            return ""
        return value.strip().lower().strip(".")
