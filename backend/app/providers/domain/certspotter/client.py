# backend/app/providers/domain/certspotter/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_certspotter.py (MIT licensed)
# Copyright (c) bcoles.
import base64
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class CertSpotterProvider(BaseProviderClient):
    name = "certspotter"
    base_url = "https://api.certspotter.com/v1/issuances"

    def __init__(
        self, api_key: str = "", timeout_seconds: int = 15, max_pages: int = 5
    ):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._max_pages = max_pages

    async def get_certificates(self, domain: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="CertSpotter API key is required",
                retryable=False,
            )

        try:
            max_pages = int(self._max_pages)
        except (TypeError, ValueError) as exc:
            raise ProviderError(
                message="Invalid certspotter option: max_pages must be an integer",
                retryable=False,
            ) from exc
        max_pages = max(1, min(max_pages, 20))

        findings = []
        evidence = []
        domain = domain.strip().lower()
        if not domain:
            return findings

        hosts: set[str] = set()
        page = 0
        after = ""
        total_records = 0
        while page < max_pages:
            payload = await self._query_issuances(domain, api_key, after)
            if not payload:
                break
            page += 1
            total_records += len(payload)
            last_id = None

            for row in payload:
                if not isinstance(row, dict):
                    continue
                last_id = row.get("id")
                dns_names = row.get("dns_names")
                if not isinstance(dns_names, list):
                    continue
                for name in dns_names:
                    host = str(name).strip().lower().replace("*.", "")
                    if not host or host == domain:
                        continue
                    hosts.add(host)
            if not last_id:
                break
            after = str(last_id)

        for host in sorted(hosts):
            findings.append(
                dict(
                    provider=self.name,
                    category="domain_security",
                    title="Certificate issuance hostname",
                    description=f"CertSpotter observed certificate hostname {host} for {domain}",
                    entity_type="hostname",
                    entity_value=host,
                    confidence=0.75,
                    tags=["certificate_transparency", "passive"],
                )
            )

        if total_records > 0:
            evidence.append(
                dict(
                    source=self.name,
                    description=f"CertSpotter lookup for {domain}",
                    raw={"domain": domain, "records": total_records, "pages": page},
                    confidence=0.75,
                )
            )

        return findings

    async def _query_issuances(
        self, domain: str, api_key: str, after: str
    ) -> list[dict[str, Any]]:
        params = {
            "domain": domain,
            "include_subdomains": "true",
            "match_wildcards": "true",
            "after": after,
            "expand": "dns_names",
        }
        url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
        basic = base64.b64encode(f"{api_key}:".encode()).decode("utf-8")
        headers = {
            "Accept": "application/json",
            "Authorization": f"Basic {basic}",
        }

        payload = await self._get(
            url, label="CertSpotter", headers=headers, timeout=self._timeout_seconds
        )
        if not payload:
            return []
        if not isinstance(payload, list):
            raise ProviderError(
                message="CertSpotter schema changed: expected list payload",
                retryable=False,
            )
        return payload
