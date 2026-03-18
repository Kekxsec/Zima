# backend/app/providers/domain/mnemonic/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_mnemonic.py (MIT licensed)
from backend.app.providers.base.client import BaseProviderClient


class MnemonicProvider(BaseProviderClient):
    name = "mnemonic"
    base_url = "https://api.mnemonic.no/pdns/v3"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def lookup_domain(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        headers: dict = {"Accept": "application/json"}
        if api_key:
            headers["Argus-API-Key"] = api_key
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "ip_address"}:
                continue
            val = _value.strip()
            payload = {"query": val, "limit": 25, "offset": 0}
            url = f"{self.base_url}/search"
            data = self._fetch_post(url, headers, payload)
            records = data.get("data", []) if isinstance(data, dict) else []
            if not isinstance(records, list):
                continue
            for rec in records[:25]:
                if not isinstance(rec, dict):
                    continue
                query = str(rec.get("query", "")).strip().rstrip(".")
                answer = str(rec.get("answer", "")).strip().rstrip(".")
                key = f"{query}:{answer}"
                if not query or not answer or key in seen:
                    continue
                seen.add(key)
                findings.append(
                    dict(
                        provider=self.name,
                        category="passive_dns",
                        title=f"Mnemonic DNS: {query}",
                        description=f"Passive DNS: {query} → {answer}",
                        entity_type="hostname",
                        entity_value=query,
                        confidence=0.78,
                        tags=["mnemonic", "passive_dns", "passive"],
                    )
                )
            if records:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Mnemonic passive DNS for {val}",
                        raw={"count": len(records)},
                        confidence=0.78,
                    )
                )
        return findings

    async def _fetch_post(self, url: str, headers: dict, payload: dict) -> dict:
        return await self._post(
            url,
            json_data=payload,
            label="Mnemonic",
            headers=headers,
            timeout=self._timeout_seconds,
        )
