# backend/app/providers/domain/viewdns/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_viewdns.py (MIT licensed)
# Copyright (c) Steve Micallef.
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ViewDNSProvider(BaseProviderClient):
    name = "viewdns"
    base_url = "https://api.viewdns.info"

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
                message="ViewDNS API key is required",
                retryable=False,
            )

        findings = []
        evidence = []
        try:
            max_pages = int(self._max_pages)
        except (TypeError, ValueError) as exc:
            raise ProviderError(
                message="Invalid viewdns option: max_pages must be an integer",
                retryable=False,
            ) from exc
        max_pages = max(1, min(max_pages, 20))
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            mapping = self._mapping_for_entity(_entity_type)
            if mapping is None:
                continue
            querytype, attr, responsekey, valuekey, bucket = mapping
            target = _value.strip().lower()
            if not target:
                continue

            page = 1
            aggregate: list[dict[str, Any]] = []
            while page <= max_pages:
                payload = await self._query(api_key, querytype, attr, target, page)
                if not payload:
                    break

                response = payload.get("response")
                if not isinstance(response, dict):
                    break
                rows = response.get(responsekey, [])
                if not isinstance(rows, list):
                    raise ProviderError(
                        message="ViewDNS schema changed: expected list response",
                        retryable=False,
                    )
                aggregate.extend(rows)
                # API page size thresholds based on SpiderFoot logic.
                threshold = 1000 if querytype == "reversewhois" else 10000
                if len(rows) < threshold:
                    break
                page += 1

            seen = set()
            for row in aggregate:
                if not isinstance(row, dict):
                    continue
                candidate = str(row.get(valuekey, "")).strip().lower()
                if not candidate or candidate == target:
                    continue
                if candidate in seen:
                    continue
                seen.add(candidate)
                findings.append(
                    dict(
                        provider=self.name,
                        category=bucket,
                        title="ViewDNS related entity",
                        description=f"ViewDNS {querytype} discovered {candidate} from {target}",
                        entity_type="hostname",
                        entity_value=candidate,
                        confidence=0.7,
                        tags=["passive", "enrichment", querytype],
                    )
                )

            if aggregate:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"ViewDNS {querytype} lookup for {target}",
                        raw={
                            "querytype": querytype,
                            "target": target,
                            "records": len(aggregate),
                        },
                        confidence=0.7,
                    )
                )

        return findings

    async def _query(
        self, api_key: str, querytype: str, attr: str, value: str, page: int
    ) -> dict[str, Any]:
        params = {
            "apikey": api_key,
            attr: value,
            "page": str(page),
            "output": "json",
        }
        url = f"{self.base_url}/{querytype}/?{urllib.parse.urlencode(params)}"

        try:
            response = await self._get(url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="ViewDNS request failed",
                retryable=True,
            ) from exc
        self._check_status_errors(response, "ViewDNS")
        if response.status_code not in {200, 400}:
            raise ProviderError(
                message="ViewDNS returned unexpected response",
                retryable=False,
                status_code=response.status_code,
            )
        if (
            response.content or ""
        ).strip() == "Query limit reached for the supplied API key.":
            raise ProviderError(
                message="ViewDNS API query limit reached",
                retryable=True,
                status_code=response.status_code,
            )
        payload = self._parse_json(response, "ViewDNS")
        if not isinstance(payload, dict):
            raise ProviderError(
                message="ViewDNS schema changed: expected object payload",
                retryable=False,
            )
        if not payload.get("query"):
            # Usually indicates bad request or transient upstream behavior.
            return {}
        return payload

    @staticmethod
    def _mapping_for_entity(entity_type: str) -> tuple[str, str, str, str, str] | None:
        if entity_type == "email":
            return ("reversewhois", "q", "matches", "domain", "attack_surface")
        if entity_type == "ip_address":
            return ("reverseip", "host", "domains", "name", "infrastructure_intel")
        if entity_type == "domain":
            return ("reversens", "ns", "domains", "domain", "domain_security")
        return None
