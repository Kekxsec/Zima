# backend/app/providers/domain/c99/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_c99.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class C99Provider(BaseProviderClient):
    name = "c99"
    base_url = "https://api.c99.nl"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def enumerate_subdomains(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(message="C99 API key is required", retryable=False)
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            val = _value.strip()
            if _entity_type == "domain":
                url = f"{self.base_url}/subdomainfinder?key={api_key}&domain={urllib.parse.quote(val)}&json"
                data = self._fetch(url)
                subdomains = (
                    data.get("subdomains", []) if isinstance(data, dict) else []
                )
                if not isinstance(subdomains, list):
                    continue
                for sub in subdomains[:30]:
                    host = str(
                        sub.get("subdomain", "") if isinstance(sub, dict) else sub
                    ).strip()
                    if not host or host in seen:
                        continue
                    seen.add(host)
                    findings.append(
                        dict(
                            provider=self.name,
                            category="subdomain",
                            title=f"C99 subdomain: {host}",
                            description=f"Subdomain of {val}: {host}",
                            entity_type="hostname",
                            entity_value=host,
                            confidence=0.75,
                            tags=["c99", "subdomain", "passive"],
                        )
                    )
                if subdomains:
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"C99 subdomains for {val}",
                            raw={"count": len(subdomains)},
                            confidence=0.75,
                        )
                    )
            elif _entity_type == "ip_address":
                url = f"{self.base_url}/geoip?key={api_key}&host={urllib.parse.quote(val)}&json"
                data = self._fetch(url)
                if isinstance(data, dict) and data.get("success"):
                    country = str(data.get("country_name", "")).strip()
                    org = str(data.get("organization", "")).strip()
                    if country or org:
                        desc = f"GeoIP for {val}: {country}" + (
                            f" ({org})" if org else ""
                        )
                        findings.append(
                            dict(
                                provider=self.name,
                                category="geo_info",
                                title=f"C99 GeoIP: {val}",
                                description=desc,
                                entity_type="ip_address",
                                entity_value=val,
                                confidence=0.70,
                                tags=["c99", "geoip", "passive"],
                            )
                        )
                        evidence.append(
                            dict(
                                source=self.name,
                                description=f"C99 GeoIP for {val}",
                                raw={"country": country, "org": org},
                                confidence=0.70,
                            )
                        )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="C99", timeout=self._timeout_seconds)
