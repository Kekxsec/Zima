# backend/app/providers/ip/censys/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_censys.py (MIT licensed)
import base64
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class CensysProvider(BaseProviderClient):
    name = "censys"
    base_url = "https://search.censys.io/api/v2"

    def __init__(
        self, api_id: str = "", api_secret: str = "", timeout_seconds: int = 15
    ):
        self._api_id = api_id
        self._api_secret = api_secret
        self._timeout_seconds = timeout_seconds

    async def search_hosts(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        api_id = str(self._api_id).strip()
        api_secret = str(self._api_secret).strip()
        if not api_id or not api_secret:
            raise ProviderError(
                message="Censys API ID and secret are required", retryable=False
            )
        creds = base64.b64encode(f"{api_id}:{api_secret}".encode()).decode()
        headers = {"Authorization": f"Basic {creds}", "Accept": "application/json"}
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"ip_address", "domain"}:
                continue
            q = _value.strip()
            params = urllib.parse.urlencode({"q": q, "per_page": "25"})
            url = f"{self.base_url}/hosts/search?{params}"
            data = self._fetch(url, headers)
            hits = data.get("result", {}).get("hits", [])
            if not isinstance(hits, list):
                continue
            for hit in hits[:20]:
                ip = str(hit.get("ip", "")).strip()
                if not ip:
                    continue
                findings.append(
                    dict(
                        provider=self.name,
                        category="host_discovery",
                        title=f"Censys host: {ip}",
                        description=f"Censys found host {ip} associated with {q}",
                        entity_type="ip_address",
                        entity_value=ip,
                        confidence=0.80,
                        tags=["censys", "passive"],
                    )
                )
            if hits:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Censys search for {q}",
                        raw={"count": len(hits)},
                        confidence=0.80,
                    )
                )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Censys", headers=headers, timeout=self._timeout_seconds
        )
