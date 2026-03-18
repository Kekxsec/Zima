# backend/app/providers/ip/bingsharedip/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_bingsharedip.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class BingSharedIPProvider(BaseProviderClient):
    name = "bingsharedip"
    base_url = "https://api.bing.microsoft.com/v7.0/search"

    def __init__(
        self, api_key: str = "", timeout_seconds: int = 15, max_results: int = 20
    ):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._max_results = max_results

    async def get_network_info(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="Bing API key is required",
                retryable=False,
            )
        max_results = int(self._max_results)
        max_results = max(1, min(max_results, 50))

        findings = []
        evidence = []
        seen_hosts = set()
        max_netblock_hosts = 32
        max_netblock_hosts = max(1, min(max_netblock_hosts, 512))

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            ips = []
            if _entity_type == "ip_address":
                ip_value = _value.strip()
                if not self._is_valid_ip(ip_value):
                    raise ProviderError(
                        message=f"Unsupported Bing shared-IP input: {ip_value}",
                        retryable=False,
                    )
                ips = [ip_value]
            elif _entity_type == "netblock":
                netblock = _value.strip()
                try:
                    network = ipaddress.ip_network(netblock, strict=False)
                except ValueError as exc:
                    raise ProviderError(
                        message=f"Unsupported Bing netblock input: {netblock}",
                        retryable=False,
                    ) from exc
                for idx, ip in enumerate(network.hosts()):
                    if idx >= max_netblock_hosts:
                        break
                    ips.append(str(ip))

            for ip in ips:
                urls = await self._search_urls(f"ip:{ip}", api_key, max_results)
                host_count = 0
                for url in urls:
                    host = (urllib.parse.urlparse(url).hostname or "").lower()
                    if not host or host == ip:
                        continue
                    if host in seen_hosts:
                        continue
                    seen_hosts.add(host)
                    host_count += 1
                    findings.append(
                        dict(
                            provider=self.name,
                            category="infrastructure_intel",
                            title="Potential co-hosted site",
                            description=f"Bing shared-IP search associated host {host} with IP {ip}",
                            entity_type="hostname",
                            entity_value=host,
                            confidence=0.65,
                            tags=["shared_ip", "cohost", "passive"],
                        )
                    )
                if host_count:
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"Bing shared-IP search results for {ip}",
                            raw={"ip": ip, "host_count": host_count},
                            confidence=0.65,
                        )
                    )

        return findings

    async def _search_urls(
        self, query: str, api_key: str, max_results: int
    ) -> list[str]:
        params = urllib.parse.urlencode({"q": query, "count": str(max_results)})
        url = f"{self.base_url}?{params}"
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        payload = await self._get(
            url, label="BingSharedIP", headers=headers, timeout=self._timeout_seconds
        )
        if not isinstance(payload, dict):
            raise ProviderError(
                message="Bing schema changed: expected object payload",
                retryable=False,
            )
        webpages = payload.get("webPages", {})
        if webpages is None:
            return []
        if not isinstance(webpages, dict):
            raise ProviderError(
                message="Bing schema changed: expected webPages object",
                retryable=False,
            )
        values = webpages.get("value", [])
        if not isinstance(values, list):
            raise ProviderError(
                message="Bing schema changed: expected webPages.value list",
                retryable=False,
            )
        return [
            str(v.get("url", "")).strip()
            for v in values
            if isinstance(v, dict) and str(v.get("url", "")).strip()
        ]

    @staticmethod
    def _is_valid_ip(value: str) -> bool:
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False
