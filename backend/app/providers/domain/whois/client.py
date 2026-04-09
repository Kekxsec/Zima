# backend/app/providers/domain/whois/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_whois.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)

# WHOIS confidence: 0.85 reflects that WHOIS data is authoritative (public registry)
# but may be privacy-redacted. Constant is intentional — we don't vary it by field
# completeness because partial records are still high-quality passive evidence.
_WHOIS_CONFIDENCE = 0.85


class WhoisProvider(BaseProviderClient):
    name = "whois"
    base_url = "https://www.whoisxmlapi.com/whoisserver/WhoisService"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def lookup_whois(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(message="WHOIS API key is required", retryable=False)
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "ip_address"}:
                continue
            val = _value.strip()
            params = urllib.parse.urlencode(
                {"apiKey": api_key, "domainName": val, "outputFormat": "JSON"}
            )
            url = f"{self.base_url}?{params}"
            data = await self._fetch(url)
            record = data.get("WhoisRecord", {})
            if not isinstance(record, dict):
                continue
            registrant = record.get("registrant", {}) or {}
            registrar = str(record.get("registrarName", "") or "").strip()
            created = str(record.get("createdDate", "") or "").strip()
            expires = str(record.get("expiresDate", "") or "").strip()
            org = str(
                registrant.get("organization", "") or registrant.get("name", "") or ""
            ).strip()
            if registrar or org:
                findings.append(
                    dict(
                        provider=self.name,
                        category="whois",
                        title=f"WHOIS data for {val}",
                        description=f"Registrar: {registrar}, Registrant: {org}, Created: {created}, Expires: {expires}",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=_WHOIS_CONFIDENCE,
                        tags=["whois", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"WHOIS record for {val}",
                        raw={
                            "registrar": registrar,
                            "org": org,
                            "created": created,
                            "expires": expires,
                        },
                        confidence=_WHOIS_CONFIDENCE,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Whois", timeout=self._timeout_seconds)
