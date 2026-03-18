# backend/app/providers/breach/wikileaks/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_wikileaks.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class WikileaksProvider(BaseProviderClient):
    name = "wikileaks"
    base_url = "https://search.wikileaks.org/api"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def search_documents(
        self,
        *,
        domain: str | None = None,
        email: str | None = None,
        name: str | None = None,
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        if name is not None:
            _inputs.append(("name", name))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "email", "human_name"}:
                continue
            val = _value.strip()
            params = urllib.parse.urlencode(
                {"query": val, "include_external_sources": "false"}
            )
            url = f"{self.base_url}/?{params}"
            data = self._fetch(url)
            results = data.get("results", []) if isinstance(data, dict) else []
            if not isinstance(results, list):
                continue
            if results:
                findings.append(
                    dict(
                        provider=self.name,
                        category="leak_mention",
                        title=f"WikiLeaks mention: {val}",
                        description=f"{val} found in {len(results)} WikiLeaks document(s)",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.78,
                        tags=["wikileaks", "leak", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"WikiLeaks search for {val}",
                        raw={"count": len(results)},
                        confidence=0.78,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Wikileaks", timeout=self._timeout_seconds)
