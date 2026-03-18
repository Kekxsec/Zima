# backend/app/providers/ip/ripe/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_ripe.py (MIT licensed)
# Copyright (c) Steve Micallef.
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class RipeProvider(BaseProviderClient):
    name = "ripe"
    base_url = "https://rest.db.ripe.net/search.json"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def get_network_info(
        self,
        *,
        asn: str | None = None,
        domain: str | None = None,
        ip_address: str | None = None,
    ) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen: set[str] = set()

        _inputs: list[tuple[str, str]] = []
        if asn is not None:
            _inputs.append(("asn", asn))
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"ip_address", "netblock", "bgp_asn", "domain"}:
                return findings
            target = _value.strip()
            params = urllib.parse.urlencode(
                {"query-string": target, "flags": "no-filtering"}
            )
            url = f"{self.base_url}?{params}"
            data = self._fetch(url)
            objects = data.get("objects", {}).get("object", [])
            if not isinstance(objects, list):
                continue
            for obj in objects:
                attrs = obj.get("attributes", {}).get("attribute", [])
                if not isinstance(attrs, list):
                    continue
                name_val = ""
                for attr in attrs:
                    if not isinstance(attr, dict):
                        continue
                    if attr.get("name") == "inetnum" or attr.get("name") == "inet6num":
                        name_val = str(attr.get("value", "")).strip()
                    elif (
                        attr.get("name") in {"netname", "org-name", "descr"}
                        and not name_val
                    ):
                        name_val = str(attr.get("value", "")).strip()
                if not name_val or name_val in seen:
                    continue
                seen.add(name_val)
                findings.append(
                    dict(
                        provider=self.name,
                        category="network_info",
                        title=f"RIPE NCC record: {name_val}",
                        description=f"RIPE NCC database entry for {target}: {name_val}",
                        entity_type=_entity_type,
                        entity_value=target,
                        confidence=0.75,
                        tags=["ripe", "whois", "network_info", "passive"],
                    )
                )
            if objects:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"RIPE NCC results for {target}",
                        raw={"count": len(objects)},
                        confidence=0.75,
                    )
                )

        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Ripe", timeout=self._timeout_seconds)
