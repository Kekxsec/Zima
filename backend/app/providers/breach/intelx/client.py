# backend/app/providers/breach/intelx/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_intelx.py (MIT licensed)
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class IntelxProvider(BaseProviderClient):
    name = "intelx"
    base_url = "https://2.intelx.io"

    def __init__(self, api_key: str = "", timeout_seconds: int = 30):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search_leaks(
        self,
        *,
        domain: str | None = None,
        email: str | None = None,
        ip_address: str | None = None,
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="IntelligenceX API key is required", retryable=False
            )
        headers = {"x-key": api_key, "Content-Type": "application/json"}
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "email", "ip_address"}:
                continue
            val = _value.strip()
            # Start a search
            payload = {
                "term": val,
                "buckets": [],
                "lookuplevel": 0,
                "maxresults": 10,
                "timeout": 5,
                "datefrom": "",
                "dateto": "",
                "sort": 2,
                "media": 0,
                "terminate": [],
            }
            search_data = self._fetch_post(
                f"{self.base_url}/intelligent/search", headers, payload
            )
            search_id = (
                search_data.get("id", "") if isinstance(search_data, dict) else ""
            )
            if not search_id:
                continue
            # Get results
            results_data = self._fetch(
                f"{self.base_url}/intelligent/search/result?id={search_id}&limit=10&offset=0",
                headers,
            )
            records = (
                results_data.get("records", [])
                if isinstance(results_data, dict)
                else []
            )
            if not isinstance(records, list):
                continue
            if records:
                findings.append(
                    dict(
                        provider=self.name,
                        category="data_leak",
                        title=f"IntelX: {val[:60]}",
                        description=f"{val} found in {len(records)} IntelligenceX record(s)",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.80,
                        tags=["intelx", "leak", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"IntelligenceX results for {val}",
                        raw={"count": len(records)},
                        confidence=0.80,
                    )
                )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Intelx", headers=headers, timeout=self._timeout_seconds
        )

    async def _fetch_post(self, url: str, headers: dict, payload: dict) -> dict:
        return await self._post(
            url,
            json_data=payload,
            label="Intelx",
            headers=headers,
            timeout=self._timeout_seconds,
        )
