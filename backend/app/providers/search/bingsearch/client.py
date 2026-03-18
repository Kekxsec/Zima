# backend/app/providers/search/bingsearch/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_bingsearch.py (MIT licensed)
# Copyright (c) Steve Micallef.
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class BingSearchProvider(BaseProviderClient):
    name = "bingsearch"
    base_url = "https://api.bing.microsoft.com/v7.0/search"

    def __init__(
        self, api_key: str = "", timeout_seconds: int = 15, max_results: int = 20
    ):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._max_results = max_results

    async def search_web(
        self, *, domain: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="Bing API key is required",
                retryable=False,
            )
        max_results = int(self._max_results)
        max_results = max(1, min(max_results, 50))

        findings = []
        evidence = []
        seen = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if url is not None:
            _inputs.append(("url", url))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "hostname"}:
                continue
            target = _value.strip().lower()
            if not target:
                continue

            urls = await self._search_urls(f"site:{target}", api_key, max_results)
            internal_count = 0
            for url in urls:
                host = urllib.parse.urlparse(url).hostname or ""
                host = host.lower()
                if not host.endswith(target):
                    continue
                key = ("url", url)
                if key in seen:
                    continue
                seen.add(key)
                internal_count += 1
                findings.append(
                    dict(
                        provider=self.name,
                        category="attack_surface",
                        title="Internal link found via Bing",
                        description=f"Bing search discovered internal URL for {target}",
                        entity_type="url",
                        entity_value=url,
                        confidence=0.7,
                        tags=["search", "bing", "passive"],
                    )
                )
            if internal_count:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Bing site search results for {target}",
                        raw={"target": target, "internal_url_count": internal_count},
                        confidence=0.7,
                    )
                )

        return findings

    async def _search_urls(
        self, query: str, api_key: str, max_results: int
    ) -> list[str]:
        params = urllib.parse.urlencode({"q": query, "count": str(max_results)})
        url = f"{self.base_url}?{params}"
        headers = {"Ocp-Apim-Subscription-Key": api_key}
        payload = await self._get(
            url, label="BingSearch", headers=headers, timeout=self._timeout_seconds
        )
        if not isinstance(payload, dict):
            raise ProviderError(
                message="Bing schema changed: expected object payload",
                retryable=False,
            )

        webpages = payload.get("webPages", {})
        if webpages is None:
            return []
        if not isinstance(webpages, dict):
            raise ProviderError(
                message="Bing schema changed: expected webPages object",
                retryable=False,
            )
        values = webpages.get("value", [])
        if not isinstance(values, list):
            raise ProviderError(
                message="Bing schema changed: expected webPages.value list",
                retryable=False,
            )
        out = []
        for value in values:
            if not isinstance(value, dict):
                continue
            candidate = str(value.get("url", "")).strip()
            if candidate:
                out.append(candidate)
        return out
