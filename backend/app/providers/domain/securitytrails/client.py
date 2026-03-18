# backend/app/providers/domain/securitytrails/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_securitytrails.py (MIT licensed)
# Copyright (c) Steve Micallef.
import json
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class SecurityTrailsProvider(BaseProviderClient):
    name = "securitytrails"
    base_url = "https://api.securitytrails.com/v1"

    def __init__(
        self, api_key: str = "", timeout_seconds: int = 15, max_pages: int = 5
    ):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._max_pages = max_pages

    async def lookup_domain(
        self,
        *,
        domain: str | None = None,
        email: str | None = None,
        ip_address: str | None = None,
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="SecurityTrails API key is required",
                retryable=False,
            )

        findings = []
        evidence = []
        try:
            max_pages = int(self._max_pages)
        except (TypeError, ValueError) as exc:
            raise ProviderError(
                message="Invalid securitytrails option: max_pages must be an integer",
                retryable=False,
            ) from exc
        max_pages = max(1, min(max_pages, 20))
        headers = {"APIKEY": api_key, "Content-Type": "application/json"}

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

            if _entity_type == "domain":
                subs = await self._query_subdomains(value, headers)
                for sub in sorted(set(subs)):
                    host = f"{sub}.{value}"
                    findings.append(
                        dict(
                            provider=self.name,
                            category="domain_security",
                            title="Passive DNS subdomain",
                            description=f"SecurityTrails found subdomain {host}",
                            entity_type="hostname",
                            entity_value=host,
                            confidence=0.7,
                            tags=["passive_dns", "passive"],
                        )
                    )
                if subs:
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"SecurityTrails subdomain lookup for {value}",
                            raw={"domain": value, "subdomain_count": len(subs)},
                            confidence=0.7,
                        )
                    )

            if _entity_type == "email":
                records = await self._query_search(
                    "whois_email", value, headers, max_pages
                )
                hosts = {
                    str(r.get("hostname", "")).strip().lower()
                    for r in records
                    if isinstance(r, dict)
                }
                hosts = {h for h in hosts if h}
                for host in sorted(hosts):
                    findings.append(
                        dict(
                            provider=self.name,
                            category="account_exposure",
                            title="WHOIS-linked hostname",
                            description=f"SecurityTrails reverse-WHOIS found {host} from {value}",
                            entity_type="hostname",
                            entity_value=host,
                            confidence=0.65,
                            tags=["reverse_whois", "passive"],
                        )
                    )
                if records:
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"SecurityTrails reverse-WHOIS lookup for {value}",
                            raw={"email": value, "record_count": len(records)},
                            confidence=0.65,
                        )
                    )

            if _entity_type == "ip_address":
                records = await self._query_search("ipv4", value, headers, max_pages)
                hosts = {
                    str(r.get("hostname", "")).strip().lower()
                    for r in records
                    if isinstance(r, dict)
                }
                hosts = {h for h in hosts if h and h != value}
                for host in sorted(hosts):
                    findings.append(
                        dict(
                            provider=self.name,
                            category="infrastructure_intel",
                            title="Co-hosted hostname",
                            description=f"SecurityTrails found co-hosted hostname {host} on {value}",
                            entity_type="hostname",
                            entity_value=host,
                            confidence=0.65,
                            tags=["cohost", "passive"],
                        )
                    )
                if records:
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"SecurityTrails reverse-IP lookup for {value}",
                            raw={"ip": value, "record_count": len(records)},
                            confidence=0.65,
                        )
                    )

        return findings

    async def _query_subdomains(
        self, domain: str, headers: dict[str, str]
    ) -> list[str]:
        url = f"{self.base_url}/domain/{domain}/subdomains"
        payload = await self._get_json(url, headers)
        if not payload:
            return []
        subs = payload.get("subdomains", [])
        if not isinstance(subs, list):
            raise ProviderError(
                message="SecurityTrails schema changed: expected subdomains list",
                retryable=False,
            )
        return [str(sub).strip().lower() for sub in subs if str(sub).strip()]

    async def _query_search(
        self, filter_key: str, value: str, headers: dict[str, str], max_pages: int
    ) -> list[dict]:
        records: list[dict] = []
        for page in range(1, max_pages + 1):
            url = f"{self.base_url}/search/list/?page={page}"
            body = json.dumps({"filter": {filter_key: value}})
            payload = await self._get_json(url, headers, post_data=body)
            if not payload:
                break
            page_records = payload.get("records", [])
            if not isinstance(page_records, list):
                raise ProviderError(
                    message="SecurityTrails schema changed: expected records list",
                    retryable=False,
                )
            records.extend(page_records)
            if len(page_records) < 100:
                break
        return records

    async def _get_json(
        self, url: str, headers: dict[str, str], post_data: str | None = None
    ) -> dict:
        try:
            if post_data is None:
                response = await self._get(
                    url, headers=headers, timeout=self._timeout_seconds
                )
            else:
                response = await self._post(
                    url, data=post_data, headers=headers, timeout=self._timeout_seconds
                )
        except Exception as exc:
            raise ProviderError(
                message="SecurityTrails request failed",
                retryable=True,
            ) from exc
        self._check_status_errors(response, "SecurityTrails")
        if response.status_code not in {200, 400}:
            raise ProviderError(
                message="SecurityTrails returned unexpected response",
                retryable=False,
                status_code=response.status_code,
            )
        payload = self._parse_json(response, "SecurityTrails")
        if not isinstance(payload, dict):
            raise ProviderError(
                message="SecurityTrails schema changed: expected object payload",
                retryable=False,
            )
        return payload
