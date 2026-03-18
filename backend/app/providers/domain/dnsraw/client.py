# backend/app/providers/domain/dnsraw/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_dnsraw.py (MIT licensed)
# Copyright (c) Steve Micallef.
from backend.app.providers.base.utils import ResolverFunc, default_resolver

_RECORD_TYPES = ("TXT", "SPF", "DMARC", "DKIM", "SOA", "CAA")


from backend.app.providers.base.client import BaseProviderClient


class DnsRawProvider(BaseProviderClient):
    name = "dnsraw"

    def __init__(
        self, resolver: ResolverFunc = default_resolver, timeout_seconds: float = 5.0
    ):
        self._resolver = resolver
        self._timeout_seconds = timeout_seconds

    async def resolve_dns(self, domain: str) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen: set[str] = set()

        domain = domain.strip().lower().strip(".")
        if not domain:
            return findings
        for record_type in _RECORD_TYPES:
            query = f"_dmarc.{domain}" if record_type == "DMARC" else domain
            try:
                results = self._resolver(query, (record_type), self._timeout_seconds)
            except Exception:
                return findings
            for rec in results:
                rec = str(rec).strip()
                if not rec:
                    continue
                key = f"{record_type}:{rec[:80]}"
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    dict(
                        provider=self.name,
                        category="dns_discovery",
                        title=f"DNS {record_type} record found",
                        description=f"{domain} {record_type}: {rec[:120]}",
                        entity_type="domain",
                        entity_value=domain,
                        confidence=0.85,
                        tags=["dns", "dnsraw", record_type.lower(), "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"DNS raw {record_type} record for {domain}",
                        raw={"domain": domain, "type": record_type, "value": rec},
                        confidence=0.85,
                    )
                )

        return findings
