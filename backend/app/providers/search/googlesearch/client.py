# backend/app/providers/search/googlesearch/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_googlesearch.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class GooglesearchProvider(BaseProviderClient):
    name = "googlesearch"
    base_url = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: str = "", cse_id: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._cse_id = cse_id
        self._timeout_seconds = timeout_seconds

    async def search_web(
        self,
        *,
        domain: str | None = None,
        name: str | None = None,
        url: str | None = None,
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        cse_id = str(self._cse_id).strip()
        if not api_key or not cse_id:
            raise ProviderError(
                message="Google API key and CSE ID are required", retryable=False
            )
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if name is not None:
            _inputs.append(("name", name))
        if url is not None:
            _inputs.append(("url", url))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "human_name"}:
                continue
            val = _value.strip()
            query = f"site:{val}" if _entity_type == "domain" else val
            params = {"key": api_key, "cx": cse_id, "q": query, "num": "10"}
            url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
            data = self._fetch(url)
            items = data.get("items", []) if isinstance(data, dict) else []
            if not isinstance(items, list):
                continue
            for item in items[:10]:
                if not isinstance(item, dict):
                    continue
                link = str(item.get("link", "")).strip()
                title = str(item.get("title", "")).strip()
                if not link or link in seen:
                    continue
                seen.add(link)
                findings.append(
                    dict(
                        provider=self.name,
                        category="web_content",
                        title=f"Google: {title[:60]}",
                        description=f"Google search result for {val}: {link}",
                        entity_type="url",
                        entity_value=link,
                        confidence=0.65,
                        tags=["googlesearch", "web", "passive"],
                    )
                )
            if items:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Google search for {val}",
                        raw={"count": len(items)},
                        confidence=0.65,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Googlesearch", timeout=self._timeout_seconds)
