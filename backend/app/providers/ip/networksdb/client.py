# backend/app/providers/ip/networksdb/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_networksdb.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class NetworksdbProvider(BaseProviderClient):
    name = "networksdb"
    base_url = "https://networksdb.io/api"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_network_info(
        self, *, asn: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="NetworksDB API key is required", retryable=False
            )
        headers = {"X-Api-Key": api_key, "Accept": "application/json"}
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if asn is not None:
            _inputs.append(("asn", asn))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"ip_address", "netblock", "bgp_asn"}:
                continue
            val = _value.strip()
            if _entity_type == "ip_address":
                url = f"{self.base_url}/ip/info?ip={urllib.parse.quote(val)}"
            elif _entity_type == "bgp_asn":
                asn = val.upper().replace("AS", "")
                url = f"{self.base_url}/as/networks?asn={urllib.parse.quote(asn)}"
            else:
                return findings
            data = self._fetch(url, headers)
            org = str(
                data.get("organisation", "") or data.get("name", "") or ""
            ).strip()
            cidr = str(data.get("cidr", "") or "").strip()
            if org:
                findings.append(
                    dict(
                        provider=self.name,
                        category="network_info",
                        title=f"NetworksDB: {org}",
                        description=f"{val} belongs to {org} ({cidr})",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.75,
                        tags=["networksdb", "network_info", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"NetworksDB data for {val}",
                        raw={"org": org, "cidr": cidr},
                        confidence=0.75,
                    )
                )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Networksdb", headers=headers, timeout=self._timeout_seconds
        )
