# backend/app/providers/threat_intel/leakix/client.py
"""LeakIX — exposed services and data leak search engine client.

Two main operations for the infrastructure_exposure module:
  1. domain_leak_search  — GET /search?scope=leak&q=domain:{domain}
  2. host_lookup         — GET /host/{ip_or_domain}

Optional enrichment:
  3. subdomain_enumeration — GET /api/subdomains/{domain}

API docs: https://docs.leakix.net
Free API key available at: https://leakix.net (account registration)
"""

from __future__ import annotations

import urllib.parse
from typing import Any

import httpx

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
)

_BASE_URL = "https://leakix.net"
_TIMEOUT_SECONDS = 30
_DEFAULT_PAGE_SIZE = 10


class LeakIXProvider(BaseProviderClient):
    """LeakIX infrastructure exposure search provider.

    Requires a LeakIX API key (free tier available at leakix.net).
    """

    name = "leakix"

    def __init__(self, api_key: str, timeout_seconds: int = _TIMEOUT_SECONDS) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self._api_key = api_key
        self._headers = {
            "api-key": api_key,
            "Accept": "application/json",
        }

    async def domain_leak_search(self, domain: str) -> list[dict[str, Any]]:
        """Search for confirmed data leaks on *domain*.

        Returns a list of normalised finding dicts, one per exposed service.
        scope=leak returns only entries with confirmed data exposure.
        """
        query = f"domain:{domain}"
        url = (
            f"{_BASE_URL}/search"
            f"?{urllib.parse.urlencode({'scope': 'leak', 'q': query})}"
        )
        data = await self._get(url, label="LeakIX", headers=self._headers)

        results: list[dict[str, Any]] = data if isinstance(data, list) else []
        findings: list[dict[str, Any]] = []

        for item in results:
            if not isinstance(item, dict):
                continue
            findings.append(self._normalise(item, domain))

        return findings

    async def domain_service_search(self, domain: str) -> list[dict[str, Any]]:
        """Search for exposed services (open ports, misconfigs) on *domain*.

        scope=service — broader than leak; includes services without confirmed
        data exposure (e.g. open Redis, unauthenticated admin panels).
        """
        query = f"domain:{domain}"
        url = (
            f"{_BASE_URL}/search"
            f"?{urllib.parse.urlencode({'scope': 'service', 'q': query})}"
        )
        data = await self._get(url, label="LeakIX", headers=self._headers)

        results: list[dict[str, Any]] = data if isinstance(data, list) else []
        return [
            self._normalise(item, domain) for item in results if isinstance(item, dict)
        ]

    async def host_lookup(self, host: str) -> dict[str, Any]:
        """Fetch all known exposed services and leaks for a specific host.

        *host* may be an IP address or a domain name.
        Returns a normalised dict or {} if not found.
        """
        encoded = urllib.parse.quote(host, safe="")
        url = f"{_BASE_URL}/host/{encoded}"
        data = await self._get(url, label="LeakIX", headers=self._headers)
        if not isinstance(data, dict) or not data:
            return {}
        return self._normalise(data, host)

    async def subdomain_enumeration(self, domain: str) -> list[str]:
        """Return discovered subdomains for *domain* (from CT logs + scanning).

        Useful as a pre-pass before domain_leak_search to expand coverage.
        """
        encoded = urllib.parse.quote(domain, safe="")
        url = f"{_BASE_URL}/api/subdomains/{encoded}"
        data = await self._get(url, label="LeakIX", headers=self._headers)

        subdomains: list[str] = []
        if isinstance(data, list):
            for entry in data:
                if isinstance(entry, str):
                    subdomains.append(entry)
                elif isinstance(entry, dict):
                    sub = (
                        entry.get("subdomain") or entry.get("host") or entry.get("name")
                    )
                    if sub and isinstance(sub, str):
                        subdomains.append(sub)
        return subdomains

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise(item: dict[str, Any], queried_entity: str) -> dict[str, Any]:
        """Flatten a LeakIX result into a consistent provider finding dict.

        The module (infrastructure_exposure) is responsible for severity
        assignment — the provider must not assign severity.
        """
        leak: dict[str, Any] = item.get("leak") or {}
        dataset: dict[str, Any] = leak.get("dataset") or {}
        geoip: dict[str, Any] = item.get("geoip") or {}
        ssl: dict[str, Any] = item.get("ssl") or {}
        http: dict[str, Any] = item.get("http") or {}

        tags: list[str] = item.get("tags") or []

        return {
            "provider": "leakix",
            "category": "infrastructure_security",
            "entity_type": "domain",
            "entity_value": queried_entity,
            # Core location / identity fields
            "ip": item.get("ip", ""),
            "host": item.get("host", queried_entity),
            "port": str(item.get("port", "")),
            "protocol": item.get("protocol", ""),
            "transport": item.get("transport") or [],
            "summary": item.get("summary", ""),
            "time": item.get("time", ""),
            # Leak dataset metadata
            "has_leak": bool(leak),
            "leak_severity": leak.get("severity", ""),
            "dataset_rows": int(dataset.get("rows") or 0),
            "dataset_size_bytes": int(dataset.get("size") or 0),
            "dataset_collections": int(dataset.get("collections") or 0),
            # Network / hosting context
            "country": geoip.get("country_name", ""),
            "as_name": geoip.get("as_name", ""),
            "as_num": geoip.get("as_num"),
            # TLS
            "ssl_detected": bool(ssl.get("detected")),
            "ssl_enabled": bool(ssl.get("enabled")),
            # HTTP metadata
            "http_status": http.get("status"),
            "http_title": http.get("title", ""),
            # Tags (e.g. "open-database", "no-auth", "elasticsearch")
            "tags": tags,
            "no_auth": "no-auth" in tags,
            "raw": item,
        }

    @staticmethod
    def _check_response(resp: httpx.Response, label: str) -> None:
        """Raise typed exceptions for auth/rate-limit failures."""
        if resp.status_code in {401, 403}:
            raise ProviderAuthError(f"{label} rejected API key ({resp.status_code})")
        if resp.status_code == 429:
            raise ProviderRateLimitError(f"{label} rate limited", retryable=True)
        if resp.status_code >= 500:
            raise ProviderError(
                message=f"{label} upstream error ({resp.status_code})",
                retryable=True,
            )
