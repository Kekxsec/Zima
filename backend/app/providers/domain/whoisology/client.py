# backend/app/providers/domain/whoisology/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_whoisology.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class WhoisologyProvider(BaseProviderClient):
    name = "whoisology"
    base_url = "https://whoisology.com/api"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def lookup_whois(
        self, *, domain: str | None = None, email: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="Whoisology API key is required", retryable=False
            )
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
                params = urllib.parse.urlencode(
                    {"auth": api_key, "request": "whois", "domain": val}
                )
            else:
                params = urllib.parse.urlencode(
                    {
                        "auth": api_key,
                        "request": "reverse",
                        "field": "email",
                        "value": val,
                    }
                )
            url = f"{self.base_url}?{params}"
            data = self._fetch(url)
            if not isinstance(data, dict):
                continue
            if _entity_type == "domain":
                registrant_email = str(data.get("registrant_email", "")).strip()
                registrant_org = str(data.get("registrant_org", "")).strip()
                if registrant_email or registrant_org:
                    findings.append(
                        dict(
                            provider=self.name,
                            category="whois",
                            title=f"Whoisology: {val}",
                            description=f"WHOIS for {val}: org={registrant_org}, email={registrant_email}",
                            entity_type="domain",
                            entity_value=val,
                            confidence=0.80,
                            tags=["whoisology", "whois", "passive"],
                        )
                    )
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"Whoisology WHOIS for {val}",
                            raw={
                                "registrant_email": registrant_email,
                                "registrant_org": registrant_org,
                            },
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
                                title=f"Whoisology reverse: {d}",
                                description=f"Domain {d} registered with email {val}",
                                entity_type="domain",
                                entity_value=d,
                                confidence=0.78,
                                tags=["whoisology", "whois", "passive"],
                            )
                        )
                if domains:
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"Whoisology reverse lookup for {val}",
                            raw={"count": len(domains)},
                            confidence=0.78,
                        )
                    )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Whoisology", timeout=self._timeout_seconds)
