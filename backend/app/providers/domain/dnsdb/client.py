# backend/app/providers/domain/dnsdb/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_dnsdb.py (MIT licensed)
import json
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class DnsdbProvider(BaseProviderClient):
    name = "dnsdb"
    base_url = "https://api.dnsdb.info/dnsdb/v2/lookup"

    def __init__(self, api_key: str = "", timeout_seconds: int = 30):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def resolve_dns(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(message="DNSDB API key is required", retryable=False)
        headers = {"Accept": "application/x-ndjson", "X-API-Key": api_key}
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            val = _value.strip()
            if _entity_type == "domain":
                url = (
                    f"{self.base_url}/rrset/name/{urllib.parse.quote(val)}/ANY?limit=20"
                )
            elif _entity_type == "ip_address":
                url = f"{self.base_url}/rdata/ip/{urllib.parse.quote(val)}/ANY?limit=20"
            else:
                return findings
            content = self._fetch_ndjson(url, headers)
            for rec in content[:20]:
                rdata_list = rec.get("rdata", []) or []
                if isinstance(rdata_list, str):
                    rdata_list = [rdata_list]
                rrname = str(rec.get("rrname", "")).strip().rstrip(".")
                for rdata in rdata_list[:5]:
                    rdata = str(rdata).strip()
                    key = f"{rrname}:{rdata}"
                    if not rdata or key in seen:
                        continue
                    seen.add(key)
                    findings.append(
                        dict(
                            provider=self.name,
                            category="passive_dns",
                            title=f"DNSDB: {rrname}",
                            description=f"DNSDB passive DNS: {rrname} → {rdata}",
                            entity_type="hostname",
                            entity_value=rrname,
                            confidence=0.80,
                            tags=["dnsdb", "passive_dns", "passive"],
                        )
                    )
            if content:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"DNSDB records for {val}",
                        raw={"count": len(content)},
                        confidence=0.80,
                    )
                )
        return findings

    async def _fetch_ndjson(self, url: str, headers: dict) -> list:
        try:
            resp = await self._get(url, headers=headers, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(message="DNSDB request failed", retryable=True) from exc
        if resp.status_code in {401, 403}:
            raise ProviderError(message="DNSDB rejected API key", retryable=False)
        if resp.status_code == 404:
            return []
        if resp.status_code == 429:
            raise ProviderError(message="DNSDB rate limited", retryable=True)
        if resp.status_code >= 500:
            raise ProviderError(message="DNSDB upstream error", retryable=True)
        if resp.status_code != 200:
            raise ProviderError(message="DNSDB unexpected response", retryable=False)
        content = (
            resp.content
            if isinstance(resp.content, str)
            else resp.content.decode("utf-8", errors="replace")
        )
        records = []
        for line in content.strip().splitlines():
            try:
                rec = json.loads(line)
                if rec.get("obj"):
                    records.append(rec["obj"])
                elif isinstance(rec, dict) and "rrname" in rec:
                    records.append(rec)
            except Exception:
                pass
        return records
