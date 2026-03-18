# backend/app/providers/domain/zonefiles/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_zonefiles.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ZonefilesProvider(BaseProviderClient):
    name = "zonefiles"
    base_url = "https://api.zonefiles.io"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search_zone_files(
        self, *, domain: str | None = None, email: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="ZoneFiles API key is required", retryable=False
            )
        headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "email"}:
                continue
            val = _value.strip()
            if _entity_type == "domain":
                params = urllib.parse.urlencode({"domain": val})
                url = f"{self.base_url}/whois?{params}"
            else:
                params = urllib.parse.urlencode({"email": val, "limit": "20"})
                url = f"{self.base_url}/reverse/email?{params}"
            data = self._fetch(url, headers)
            if not isinstance(data, dict):
                continue
            if _entity_type == "domain":
                registrant = str(data.get("registrant_email", "")).strip()
                ns = data.get("nameservers", []) or []
                if registrant or ns:
                    findings.append(
                        dict(
                            provider=self.name,
                            category="whois",
                            title=f"ZoneFiles WHOIS: {val}",
                            description=f"WHOIS for {val}: registrant_email={registrant}",
                            entity_type="domain",
                            entity_value=val,
                            confidence=0.80,
                            tags=["zonefiles", "whois", "passive"],
                        )
                    )
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"ZoneFiles WHOIS for {val}",
                            raw={"registrant_email": registrant, "nameservers": ns[:5]},
                            confidence=0.80,
                        )
                    )
            else:
                domains = data.get("domains", []) or []
                for domain in (domains if isinstance(domains, list) else [])[:20]:
                    d = str(domain).strip()
                    if d and d not in seen:
                        seen.add(d)
                        findings.append(
                            dict(
                                provider=self.name,
                                category="whois",
                                title=f"ZoneFiles reverse: {d}",
                                description=f"Domain {d} registered with email {val}",
                                entity_type="domain",
                                entity_value=d,
                                confidence=0.78,
                                tags=["zonefiles", "whois", "passive"],
                            )
                        )
                if domains:
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"ZoneFiles reverse for {val}",
                            raw={"count": len(domains)},
                            confidence=0.78,
                        )
                    )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Zonefiles", headers=headers, timeout=self._timeout_seconds
        )
