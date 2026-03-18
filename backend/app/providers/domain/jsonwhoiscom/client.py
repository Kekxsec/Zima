# backend/app/providers/domain/jsonwhoiscom/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_jsonwhoiscom.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class JsonwhoiscomProvider(BaseProviderClient):
    name = "jsonwhoiscom"
    base_url = "https://jsonwhois.com/api/v1/whois"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def lookup_whois(self, domain: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="JSONWhois API key is required", retryable=False
            )
        headers = {
            "Authorization": f"Token token={api_key}",
            "Accept": "application/json",
        }
        findings, evidence = [], []
        val = domain.strip()
        url = f"{self.base_url}?{urllib.parse.urlencode({'domain': val})}"
        data = self._fetch(url, headers)
        if not isinstance(data, dict):
            return findings
        registrant = str(
            data.get("registrant_name", "")
            or data.get("registrant", {}).get("name", "")
            if isinstance(data.get("registrant"), dict)
            else ""
        ).strip()
        registrar = str(
            data.get("registrar", {}).get("name", "")
            if isinstance(data.get("registrar"), dict)
            else data.get("registrar", "")
        ).strip()
        created = str(
            data.get("created_on", "") or data.get("creation_date", "")
        ).strip()
        if registrant or registrar:
            desc = f"WHOIS for {val}: registrant={registrant or 'unknown'}, registrar={registrar or 'unknown'}"
            if created:
                desc += f", created={created}"
            findings.append(
                dict(
                    provider=self.name,
                    category="whois",
                    title=f"JSONWhois: {val}",
                    description=desc,
                    entity_type="domain",
                    entity_value=val,
                    confidence=0.78,
                    tags=["jsonwhoiscom", "whois", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"JSONWhois data for {val}",
                    raw={
                        "registrant": registrant,
                        "registrar": registrar,
                        "created": created,
                    },
                    confidence=0.78,
                )
            )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Jsonwhoiscom", headers=headers, timeout=self._timeout_seconds
        )
