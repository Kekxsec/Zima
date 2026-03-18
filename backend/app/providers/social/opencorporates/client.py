# backend/app/providers/social/opencorporates/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_opencorporates.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class OpencorporatesProvider(BaseProviderClient):
    name = "opencorporates"
    base_url = "https://api.opencorporates.com/v0.4"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def lookup_company(
        self, *, domain: str | None = None, name: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if name is not None:
            _inputs.append(("name", name))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"human_name", "domain"}:
                continue
            val = _value.strip()
            q = val.split(".")[0] if _entity_type == "domain" else val
            params: dict = {"q": q, "format": "json"}
            if api_key:
                params["api_token"] = api_key
            url = f"{self.base_url}/companies/search?{urllib.parse.urlencode(params)}"
            data = self._fetch(url)
            companies = data.get("results", {}).get("companies", [])
            if not isinstance(companies, list):
                continue
            for c in companies[:10]:
                company = c.get("company", {}) if isinstance(c, dict) else {}
                name = str(company.get("name", "")).strip()
                number = str(company.get("company_number", "")).strip()
                jurisdiction = str(company.get("jurisdiction_code", "")).strip()
                key = f"{name}:{jurisdiction}"
                if not name or key in seen:
                    continue
                seen.add(key)
                findings.append(
                    dict(
                        provider=self.name,
                        category="corporate_info",
                        title=f"OpenCorporates: {name}",
                        description=f"Company found: {name} ({number}, {jurisdiction})",
                        entity_type="human_name",
                        entity_value=name,
                        confidence=0.68,
                        tags=["opencorporates", "corporate", "passive"],
                    )
                )
            if companies:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"OpenCorporates search for {q}",
                        raw={"count": len(companies)},
                        confidence=0.68,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(
            url, label="Opencorporates", timeout=self._timeout_seconds
        )
