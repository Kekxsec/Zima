# backend/app/providers/ip/abstractapi/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_abstractapi.py (MIT licensed)
# Copyright (c) Steve Micallef.
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class AbstractAPIProvider(BaseProviderClient):
    name = "abstractapi"
    company_url = "https://companyenrichment.abstractapi.com/v1/"
    phone_url = "https://phonevalidation.abstractapi.com/v1/"
    ipgeo_url = "https://ipgeolocation.abstractapi.com/v1/"

    def __init__(
        self,
        companyenrichment_api_key: str = "",
        phonevalidation_api_key: str = "",
        ipgeolocation_api_key: str = "",
        timeout_seconds: int = 15,
    ):
        self._company_key = companyenrichment_api_key
        self._phone_key = phonevalidation_api_key
        self._ipgeo_key = ipgeolocation_api_key
        self._timeout_seconds = timeout_seconds

    async def get_geolocation(
        self,
        *,
        domain: str | None = None,
        ip_address: str | None = None,
        phone_number: str | None = None,
    ) -> list[dict[str, Any]]:
        company_key = str(self._company_key).strip()
        phone_key = str(self._phone_key).strip()
        ipgeo_key = str(self._ipgeo_key).strip()

        findings = []
        evidence = []
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        if phone_number is not None:
            _inputs.append(("phone_number", phone_number))
        for _entity_type, _value in _inputs:
            value = _value.strip()
            if not value:
                continue

            if _entity_type == "domain":
                if not company_key:
                    continue
                payload = await self._query_company(value, company_key)
                company_name = str(payload.get("name", "")).strip()
                if not company_name or company_name == "To Be Confirmed":
                    continue
                findings.append(
                    dict(
                        provider=self.name,
                        category="infrastructure_intel",
                        title="Company enrichment match",
                        description=f"AbstractAPI enriched {value} with company '{company_name}'",
                        entity_type="domain",
                        entity_value=value,
                        confidence=0.7,
                        tags=["company_enrichment", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"AbstractAPI company enrichment response for {value}",
                        raw=payload,
                        confidence=0.7,
                    )
                )

            if _entity_type == "phone":
                if not phone_key:
                    continue
                payload = await self._query_phone(value, phone_key)
                if payload.get("valid") is not True:
                    continue
                findings.append(
                    dict(
                        provider=self.name,
                        category="identity_exposure",
                        title="Phone validation enrichment",
                        description=f"AbstractAPI validated phone and enriched metadata for {value}",
                        entity_type="phone",
                        entity_value=value,
                        confidence=0.7,
                        tags=["phone_enrichment", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"AbstractAPI phone validation response for {value}",
                        raw=payload,
                        confidence=0.7,
                    )
                )

            if _entity_type == "ip_address":
                if not ipgeo_key:
                    continue
                payload = await self._query_ipgeo(value, ipgeo_key)
                findings.append(
                    dict(
                        provider=self.name,
                        category="infrastructure_intel",
                        title="IP geolocation enrichment",
                        description=f"AbstractAPI returned geolocation metadata for {value}",
                        entity_type="ip_address",
                        entity_value=value,
                        confidence=0.7,
                        tags=["ip_geolocation", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"AbstractAPI IP geolocation response for {value}",
                        raw=payload,
                        confidence=0.7,
                    )
                )

        if (
            not findings
            and not evidence
            and not (company_key or phone_key or ipgeo_key)
        ):
            raise ProviderError(
                message="At least one AbstractAPI endpoint key is required",
                retryable=False,
            )

        return findings

    async def _query_company(self, domain: str, api_key: str) -> dict:
        params = {"api_key": api_key, "domain": domain}
        return await self._get_json(self.company_url, params)

    async def _query_phone(self, phone: str, api_key: str) -> dict:
        params = {"api_key": api_key, "phone": phone}
        return await self._get_json(self.phone_url, params)

    async def _query_ipgeo(self, ip_value: str, api_key: str) -> dict:
        params = {"api_key": api_key, "ip_address": ip_value}
        return await self._get_json(self.ipgeo_url, params)

    async def _get_json(self, base_url: str, params: dict[str, str]) -> dict:
        query = urllib.parse.urlencode(params)
        url = f"{base_url}?{query}"
        try:
            response = await self._get(url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="AbstractAPI request failed",
                retryable=True,
            ) from exc
        self._check_status_errors(response, "AbstractAPI")
        payload = self._parse_json(response, "AbstractAPI")
        if not isinstance(payload, dict):
            raise ProviderError(
                message="AbstractAPI schema changed: expected object payload",
                retryable=False,
            )
        return payload
