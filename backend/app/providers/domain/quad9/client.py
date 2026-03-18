# backend/app/providers/domain/quad9/client.py
from __future__ import annotations

from typing import Any

from backend.app.providers.base.client import BaseProviderClient

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_quad9.py (MIT licensed)
# Copyright (c) Steve Micallef.
from backend.app.providers.base.utils import ResolverFunc, default_resolver


class Quad9Provider(BaseProviderClient):
    name = "quad9"
    nameservers = "9.9.9.9"

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

        if self._require_public_resolution and not self._resolve(host, ()):
            return findings
        if self._resolve(host, self.nameservers):
            return findings

        findings.append(
            dict(
                provider=self.name,
                category="reputation",
                title="Hostname blocked by Quad9 DNS",
                description=f"{host} resolved publicly but did not resolve through Quad9 DNS profile",
                entity_type="hostname",
                entity_value=host,
                confidence=0.74,
                tags=["reputation", "malicious", "quad9", "passive"],
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description=f"Quad9 resolver check for {host}",
                raw={
                    "host": host,
                    "resolver": list(self.nameservers),
                    "resolved": False,
                },
                confidence=0.74,
            )
        )

        return findings

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
