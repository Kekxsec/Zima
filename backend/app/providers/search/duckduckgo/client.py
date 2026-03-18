# backend/app/providers/search/duckduckgo/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_duckduckgo.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class DuckduckgoProvider(BaseProviderClient):
    name = "duckduckgo"
    base_url = "https://api.duckduckgo.com/"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def search_web(
        self, *, domain: str | None = None, name: str | None = None
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if name is not None:
            _inputs.append(("name", name))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "human_name"}:
                continue
            val = _value.strip()
            url = f"{self.base_url}?{urllib.parse.urlencode({'q': val, 'format': 'json', 'no_html': '1'})}"
            data = self._fetch(url)
            if not isinstance(data, dict):
                continue
            abstract = str(data.get("AbstractText", "")).strip()
            heading = str(data.get("Heading", "")).strip()
            abstract_url = str(data.get("AbstractURL", "")).strip()
            if abstract and heading:
                findings.append(
                    dict(
                        provider=self.name,
                        category="web_content",
                        title=f"DuckDuckGo: {heading}",
                        description=f"DuckDuckGo instant answer for {val}: {abstract[:200]}",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.60,
                        tags=["duckduckgo", "search", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"DuckDuckGo result for {val}",
                        raw={"heading": heading, "url": abstract_url},
                        confidence=0.60,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Duckduckgo", timeout=self._timeout_seconds)
