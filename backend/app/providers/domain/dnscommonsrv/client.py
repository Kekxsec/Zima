# backend/app/providers/domain/dnscommonsrv/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_dnscommonsrv.py (MIT licensed)
# Copyright (c) Michael Scherer.
from backend.app.providers.base.utils import ResolverFunc, default_resolver

_SRV_PREFIXES = [
    "_ldap._tcp",
    "_gc._msdcs",
    "_ldap._tcp.pdc._msdcs",
    "_ldap._tcp.gc._msdcs",
    "_kerberos._tcp.dc._msdcs",
    "_kerberos._tcp",
    "_kerberos._udp",
    "_kpasswd._tcp",
    "_kpasswd._udp",
    "_ntp._udp",
    "_sip._tcp",
    "_sip._udp",
    "_sip._tls",
    "_sips._tcp",
    "_stun._tcp",
    "_stun._udp",
    "_stuns._tcp",
    "_turn._tcp",
    "_turn._udp",
    "_turns._tcp",
    "_jabber._tcp",
    "_xmpp-client._tcp",
    "_xmpp-server._tcp",
    "_http._tcp",
    "_https._tcp",
    "_ftp._tcp",
    "_smtp._tcp",
    "_imap._tcp",
    "_imaps._tcp",
    "_pop3._tcp",
    "_pop3s._tcp",
    "_caldav._tcp",
    "_caldavs._tcp",
    "_carddav._tcp",
    "_carddavs._tcp",
]


from backend.app.providers.base.client import BaseProviderClient


class DnsCommonSrvProvider(BaseProviderClient):
    name = "dnscommonsrv"

    def __init__(
        self, resolver: ResolverFunc = default_resolver, timeout_seconds: float = 3.0
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
        for prefix in _SRV_PREFIXES:
            fqdn = f"{prefix}.{domain}"
            try:
                results = self._resolver(fqdn, ("SRV"), self._timeout_seconds)
            except Exception:
                return findings
            for rec in results:
                rec = str(rec).strip()
                if not rec or rec in seen:
                    continue
                seen.add(rec)
                findings.append(
                    dict(
                        provider=self.name,
                        category="dns_discovery",
                        title=f"SRV record found: {prefix}",
                        description=f"DNS SRV record {fqdn} resolves to {rec}",
                        entity_type="domain",
                        entity_value=domain,
                        confidence=0.80,
                        tags=["dns", "srv", "dnscommonsrv", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"SRV record: {fqdn}",
                        raw={"fqdn": fqdn, "record": rec},
                        confidence=0.80,
                    )
                )

        return findings
