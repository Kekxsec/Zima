# backend/app/providers/domain/dnsresolve/client.py
from __future__ import annotations

from typing import Any

from backend.app.providers.base.client import BaseProviderClient

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_dnsresolve.py (MIT licensed)
# Copyright (c) Steve Micallef.
from backend.app.providers.base.utils import ResolverFunc, default_resolver


class DnsResolveProvider(BaseProviderClient):
    name = "dnsresolve"

    def __init__(
        self, resolver: ResolverFunc = default_resolver, timeout_seconds: float = 5.0
    ):
        self._resolver = resolver
        self._timeout_seconds = timeout_seconds

    async def resolve_dns(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen: set[str] = set()

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "hostname"}:
                continue
            host = _value.strip().lower().strip(".")
            if not host:
                continue
            for record_type in ("A", "AAAA", "MX", "NS"):
                try:
                    results = self._resolver(host, (record_type), self._timeout_seconds)
                except Exception:
                    return findings
                for rec in results:
                    rec = str(rec).strip()
                    if not rec:
                        continue
                    key = f"{record_type}:{rec}"
                    if key in seen:
                        continue
                    seen.add(key)
                    etype = "ip_address" if record_type in ("A", "AAAA") else "hostname"
                    findings.append(
                        dict(
                            provider=self.name,
                            category="dns_resolution",
                            title=f"DNS {record_type} record: {rec}",
                            description=f"{host} {record_type} resolves to {rec}",
                            entity_type=etype,
                            entity_value=rec,
                            confidence=0.90,
                            tags=["dns", "dnsresolve", record_type.lower(), "passive"],
                        )
                    )
            if findings:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"DNS resolution results for {host}",
                        raw={"host": host, "records": list(seen)},
                        confidence=0.90,
                    )
                )

        return findings
