# backend/app/providers/ip/bgpview/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_bgpview.py (MIT licensed)
# Copyright (c) bcoles.
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class BGPViewProvider(BaseProviderClient):
    name = "bgpview"
    base_url = "https://api.bgpview.io"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def get_network_info(
        self, *, asn: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        _inputs: list[tuple[str, str]] = []
        if asn is not None:
            _inputs.append(("asn", asn))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type != "ip_address":
                continue
            ip_value = _value.strip()
            if not ip_value:
                continue

            payload = await self._query_ip(ip_value)
            data = payload.get("data")
            if not isinstance(data, dict):
                raise ProviderError(
                    message="BGPView schema changed: expected data object",
                    retryable=False,
                )

            prefixes = data.get("prefixes", [])
            if not isinstance(prefixes, list):
                raise ProviderError(
                    message="BGPView schema changed: expected prefixes list",
                    retryable=False,
                )

            asn_seen = set()
            netblock_seen = set()
            for prefix in prefixes:
                if not isinstance(prefix, dict):
                    continue
                pfx = str(prefix.get("prefix", "")).strip().lower()
                asn = prefix.get("asn")
                if not isinstance(asn, dict):
                    continue
                asn_id = str(asn.get("asn", "")).strip()
                if not pfx or not asn_id:
                    continue

                if asn_id not in asn_seen:
                    asn_seen.add(asn_id)
                    findings.append(
                        dict(
                            provider=self.name,
                            category="infrastructure_intel",
                            title="BGP ASN observed for IP",
                            description=f"BGPView associated {ip_value} with ASN {asn_id}",
                            entity_type="bgp_asn",
                            entity_value=asn_id,
                            confidence=0.75,
                            tags=["bgp", "asn", "passive"],
                        )
                    )

                if pfx not in netblock_seen:
                    netblock_seen.add(pfx)
                    findings.append(
                        dict(
                            provider=self.name,
                            category="infrastructure_intel",
                            title="BGP netblock observed for IP",
                            description=f"BGPView associated {ip_value} with netblock {pfx}",
                            entity_type="netblock",
                            entity_value=pfx,
                            confidence=0.75,
                            tags=["bgp", "netblock", "passive"],
                        )
                    )

            if prefixes:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"BGPView lookup for {ip_value}",
                        raw={
                            "ip": ip_value,
                            "prefix_count": len(prefixes),
                            "raw_data": data,
                        },
                        confidence=0.75,
                    )
                )

        return findings

    async def _query_ip(self, ip_value: str) -> dict:
        url = f"{self.base_url}/ip/{urllib.parse.quote(ip_value)}"
        payload = await self._get(url, label="BGPView", timeout=self._timeout_seconds)
        if not isinstance(payload, dict):
            raise ProviderError(
                message="BGPView schema changed: expected object payload",
                retryable=False,
            )
        if payload.get("status") != "ok":
            return {"status": "ok", "data": {"prefixes": []}}
        return payload
