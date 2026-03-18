# backend/app/providers/domain/crtsh/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_crt.py (MIT licensed)
# Copyright (c) Steve Micallef.
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class CrtShProvider(BaseProviderClient):
    name = "crtsh"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def get_certificates(self, domain: str) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []

        query_value = domain.strip().lower()
        if not query_value:
            return findings
        params = {"q": "%." + query_value, "output": "json"}
        url = "https://crt.sh/?" + urllib.parse.urlencode(params)
        payload = await self._get(url, label="CrtSh", timeout=self._timeout_seconds)
        if not isinstance(payload, list):
            raise ProviderError(
                message="crt.sh schema changed: expected list payload",
                retryable=False,
            )

        hosts, cert_ids = self._extract_hosts_and_cert_ids(payload, query_value)
        if not hosts:
            return findings

        for host in sorted(hosts):
            findings.append(
                dict(
                    provider=self.name,
                    category="domain_security",
                    title="Certificate transparency hostname",
                    description=f"Found historical certificate hostname {host} for {query_value}",
                    entity_type="hostname",
                    entity_value=host,
                    tags=["certificate_transparency", "passive"],
                )
            )

        evidence.append(
            dict(
                source=self.name,
                description=f"crt.sh lookup for {query_value}",
                raw={
                    "query": query_value,
                    "certificate_ids": sorted(cert_ids),
                    "result_count": len(payload),
                },
                confidence=0.7,
            )
        )

        return findings

    @staticmethod
    def _extract_hosts_and_cert_ids(
        payload: list[dict[str, object]], query_value: str
    ) -> tuple[set[str], set[int]]:
        hosts: set[str] = set()
        cert_ids: set[int] = set()
        for item in payload:
            cert_id = item.get("id")
            if isinstance(cert_id, int):
                cert_ids.add(cert_id)
            name_value = str(item.get("name_value", "")).strip()
            if not name_value:
                continue
            for candidate in name_value.splitlines():
                host = candidate.lower().strip().replace("*.", "")
                if not host or host == query_value:
                    continue
                hosts.add(host)
        return hosts, cert_ids
