# backend/app/providers/ip/shodan/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_shodan.py (MIT licensed)
# Copyright (c) Steve Micallef.
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ShodanProvider(BaseProviderClient):
    name = "shodan"
    base_url = "https://api.shodan.io"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search_hosts(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(message="Shodan API key is required", retryable=False)

        findings = []
        evidence = []

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type == "ip_address":
                url = f"{self.base_url}/shodan/host/{urllib.parse.quote(_value.strip())}?key={api_key}"
                data = await self._get(
                    url, label="Shodan", timeout=self._timeout_seconds
                )
                ports = data.get("ports", [])
                hostnames = data.get("hostnames", [])
                vulns = (
                    list(data.get("vulns", {}).keys())
                    if isinstance(data.get("vulns"), dict)
                    else []
                )
                org = str(data.get("org", "")).strip()
                if ports:
                    findings.append(
                        dict(
                            provider=self.name,
                            category="port_discovery",
                            title=f"Shodan: {len(ports)} open ports on {_value}",
                            description=f"Open ports: {', '.join(str(p) for p in ports[:20])}",
                            entity_type="ip_address",
                            entity_value=_value,
                            confidence=0.90,
                            tags=["shodan", "port_scan", "passive"],
                        )
                    )
                if vulns:
                    findings.append(
                        dict(
                            provider=self.name,
                            category="vulnerability",
                            title=f"Shodan: {len(vulns)} vulnerabilities on {_value}",
                            description=f"CVEs found: {', '.join(vulns[:5])}",
                            entity_type="ip_address",
                            entity_value=_value,
                            confidence=0.85,
                            tags=["shodan", "vulnerability", "passive"],
                        )
                    )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Shodan host data for {_value}",
                        raw={
                            "ports": ports,
                            "org": org,
                            "vulns": vulns[:10],
                            "hostnames": hostnames[:10],
                        },
                        confidence=0.90,
                    )
                )

            elif _entity_type == "domain":
                params = urllib.parse.urlencode(
                    {"query": f"hostname:{_value.strip()}", "key": api_key}
                )
                url = f"{self.base_url}/shodan/host/search?{params}"
                data = await self._get(
                    url, label="Shodan", timeout=self._timeout_seconds
                )
                matches = data.get("matches", [])
                if not isinstance(matches, list):
                    continue
                for match in matches[:20]:
                    ip_str = str(match.get("ip_str", "")).strip()
                    if not ip_str:
                        continue
                    findings.append(
                        dict(
                            provider=self.name,
                            category="host_discovery",
                            title=f"Shodan host for {_value}: {ip_str}",
                            description=f"IP {ip_str} associated with {_value} via Shodan",
                            entity_type="ip_address",
                            entity_value=ip_str,
                            confidence=0.80,
                            tags=["shodan", "host_discovery", "passive"],
                        )
                    )
                if matches:
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"Shodan search results for {_value}",
                            raw={"count": len(matches)},
                            confidence=0.80,
                        )
                    )

        return findings
