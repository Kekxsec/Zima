# backend/app/providers/ip/binaryedge/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_binaryedge.py (MIT licensed)
# Copyright (c) Steve Micallef.
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class BinaryEdgeProvider(BaseProviderClient):
    name = "binaryedge"
    base_url = "https://api.binaryedge.io/v2/query"

    def __init__(
        self, api_key: str = "", timeout_seconds: int = 15, max_pages: int = 5
    ):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._max_pages = max_pages

    async def search_hosts(
        self,
        *,
        domain: str | None = None,
        email: str | None = None,
        ip_address: str | None = None,
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="BinaryEdge API key is required",
                retryable=False,
            )
        max_pages = int(self._max_pages)
        max_pages = max(1, min(max_pages, 50))

        findings = []
        evidence = []
        seen = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            value = _value.strip().lower()
            if not value:
                continue

            if _entity_type == "email":
                pages = await self._query_pages(
                    f"dataleaks/email/{urllib.parse.quote(value)}", api_key, max_pages
                )
                leak_count = 0
                for page in pages:
                    events = page.get("events", [])
                    if not isinstance(events, list):
                        continue
                    for leak in events:
                        leak_name = str(leak).strip()
                        if not leak_name:
                            continue
                        key = ("email", value, leak_name)
                        if key in seen:
                            continue
                        seen.add(key)
                        leak_count += 1
                        findings.append(
                            dict(
                                provider=self.name,
                                category="breach_detection",
                                title="Compromised email event",
                                description=f"BinaryEdge reported compromised email event for {value}: {leak_name}",
                                entity_type="email",
                                entity_value=value,
                                confidence=0.8,
                                tags=["breach", "binaryedge", "passive"],
                            )
                        )
                if leak_count:
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"BinaryEdge email leak lookup for {value}",
                            raw={"email": value, "event_count": leak_count},
                            confidence=0.8,
                        )
                    )

            if _entity_type == "domain":
                pages = await self._query_pages(
                    f"domains/subdomain/{urllib.parse.quote(value)}", api_key, max_pages
                )
                host_count = 0
                for page in pages:
                    events = page.get("events", [])
                    if not isinstance(events, list):
                        continue
                    for host in events:
                        hostname = str(host).strip().lower()
                        if not hostname:
                            continue
                        key = ("domain", hostname)
                        if key in seen:
                            continue
                        seen.add(key)
                        host_count += 1
                        findings.append(
                            dict(
                                provider=self.name,
                                category="attack_surface",
                                title="Subdomain from BinaryEdge",
                                description=f"BinaryEdge discovered subdomain {hostname} for {value}",
                                entity_type="hostname",
                                entity_value=hostname,
                                confidence=0.7,
                                tags=["subdomain", "binaryedge", "passive"],
                            )
                        )
                if host_count:
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"BinaryEdge subdomain lookup for {value}",
                            raw={"domain": value, "host_count": host_count},
                            confidence=0.7,
                        )
                    )

            if _entity_type == "ip_address":
                pages = await self._query_pages(
                    f"domains/ip/{urllib.parse.quote(value)}", api_key, max_pages
                )
                host_count = 0
                for page in pages:
                    events = page.get("events", [])
                    if not isinstance(events, list):
                        continue
                    for row in events:
                        if not isinstance(row, dict):
                            continue
                        host = str(row.get("domain", "")).strip().lower()
                        if not host or host == value:
                            continue
                        key = ("ip", value, host)
                        if key in seen:
                            continue
                        seen.add(key)
                        host_count += 1
                        findings.append(
                            dict(
                                provider=self.name,
                                category="infrastructure_intel",
                                title="Passive DNS co-host from BinaryEdge",
                                description=f"BinaryEdge passive DNS associated {host} with IP {value}",
                                entity_type="hostname",
                                entity_value=host,
                                confidence=0.7,
                                tags=["passive_dns", "cohost", "binaryedge", "passive"],
                            )
                        )
                if host_count:
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"BinaryEdge passive DNS lookup for {value}",
                            raw={"ip": value, "host_count": host_count},
                            confidence=0.7,
                        )
                    )

        return findings

    async def _query_pages(self, path: str, api_key: str, max_pages: int) -> list[dict]:
        pages = []
        for page in range(1, max_pages + 1):
            payload = await self._query_page(path, api_key, page)
            if not payload:
                break
            pages.append(payload)
            if not self._has_more(payload):
                break
        return pages

    async def _query_page(self, path: str, api_key: str, page: int) -> dict:
        url = f"{self.base_url}/{path}?page={page}"
        headers = {"X-Key": api_key}
        payload = await self._get(
            url, label="BinaryEdge", headers=headers, timeout=self._timeout_seconds
        )
        if not isinstance(payload, dict):
            raise ProviderError(
                message="BinaryEdge schema changed: expected object payload",
                retryable=False,
            )
        return payload

    @staticmethod
    def _has_more(payload: dict) -> bool:
        page = payload.get("page")
        total = payload.get("total")
        pagesize = payload.get("pagesize", 100)
        if (
            not isinstance(page, int)
            or not isinstance(total, int)
            or not isinstance(pagesize, int)
        ):
            return False
        return total > pagesize * page
