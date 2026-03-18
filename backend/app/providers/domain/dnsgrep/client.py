# backend/app/providers/domain/dnsgrep/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_dnsgrep.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class DnsgrepProvider(BaseProviderClient):
    name = "dnsgrep"
    base_url = "https://dns.bufferover.run/dns"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def resolve_dns(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "ip_address"}:
                continue
            val = _value.strip()
            q = f".{val}" if _entity_type == "domain" else val
            url = f"{self.base_url}?{urllib.parse.urlencode({'q': q})}"
            data = self._fetch(url)
            fdns = data.get("FDNS_A", []) or []
            rdns = data.get("RDNS", []) or []
            all_records = list(fdns) + list(rdns)
            for record in all_records[:30]:
                parts = str(record).split(",")
                host = parts[1].strip() if len(parts) > 1 else parts[0].strip()
                if not host or host in seen:
                    continue
                seen.add(host)
                findings.append(
                    dict(
                        provider=self.name,
                        category="passive_dns",
                        title=f"DNSGrep: {host}",
                        description=f"DNS record found for {val}: {host}",
                        entity_type="hostname",
                        entity_value=host,
                        confidence=0.72,
                        tags=["dnsgrep", "passive_dns", "passive"],
                    )
                )
            if all_records:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"DNSGrep results for {val}",
                        raw={"count": len(all_records)},
                        confidence=0.72,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Dnsgrep", timeout=self._timeout_seconds)
