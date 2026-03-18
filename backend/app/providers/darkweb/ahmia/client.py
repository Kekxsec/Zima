# backend/app/providers/darkweb/ahmia/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_ahmia.py (MIT licensed)
# Copyright (c) Steve Micallef.
import re
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class AhmiaProvider(BaseProviderClient):
    name = "ahmia"
    base_url = "https://ahmia.fi/search/"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def search_darkweb(
        self,
        *,
        domain: str | None = None,
        email: str | None = None,
        url: str | None = None,
        username: str | None = None,
    ) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        if url is not None:
            _inputs.append(("url", url))
        if username is not None:
            _inputs.append(("username", username))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "email", "username"}:
                continue
            query_value = _value.strip()
            if not query_value:
                continue
            html = await self._query(query_value)
            if not html:
                continue
            links = self._extract_onion_links(html)
            for link in links:
                if link in seen:
                    continue
                seen.add(link)
                findings.append(
                    dict(
                        provider=self.name,
                        category="identity_exposure",
                        title="Darknet mention URL",
                        description=f"Ahmia search returned darknet mention for query {query_value}",
                        entity_type="url",
                        entity_value=link,
                        confidence=0.65,
                        tags=["darknet", "mention", "passive"],
                    )
                )
            if links:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Ahmia query results for {query_value}",
                        raw={"query": query_value, "result_count": len(links)},
                        confidence=0.65,
                    )
                )
        return findings

    async def _query(self, query_value: str) -> str:
        params = urllib.parse.urlencode({"q": query_value})
        url = f"{self.base_url}?{params}"
        try:
            response = await self._get(url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="Ahmia request failed",
                retryable=True,
            ) from exc

        if response.status_code == 429:
            raise ProviderError(
                message="Ahmia rate limited request",
                retryable=True,
            )
        if response.status_code >= 500:
            raise ProviderError(
                message="Ahmia upstream unavailable",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code != 200:
            raise ProviderError(
                message="Ahmia returned unexpected response",
                retryable=False,
                status_code=response.status_code,
            )
        return response.content or ""

    @staticmethod
    def _extract_onion_links(html: str) -> list[str]:
        links = re.findall(
            r"redirect_url=(.[^\"]+)\"", html, flags=re.IGNORECASE | re.DOTALL
        )
        out = []
        for link in links:
            link = link.strip()
            if not link:
                continue
            host = urllib.parse.urlparse(link).hostname or ""
            if not host.endswith(".onion"):
                continue
            out.append(link)
        return out
