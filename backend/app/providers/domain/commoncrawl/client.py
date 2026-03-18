# backend/app/providers/domain/commoncrawl/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_commoncrawl.py (MIT licensed)
import json
import urllib.parse
from typing import Any

INDEX_API = "https://index.commoncrawl.org/"
LATEST_INDEX = "CC-MAIN-2024-10"


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class CommoncrawlProvider(BaseProviderClient):
    name = "commoncrawl"

    def __init__(self, timeout_seconds: int = 60):
        self._timeout_seconds = timeout_seconds

    async def crawl_site(
        self, *, domain: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if url is not None:
            _inputs.append(("url", url))
        for _entity_type, _value in _inputs:
            if _entity_type != "domain":
                continue
            val = _value.strip()
            url = f"{INDEX_API}{LATEST_INDEX}-index?url={urllib.parse.quote(val + '/*')}&output=json&limit=20"
            try:
                resp = await self._get(url, timeout=self._timeout_seconds)
            except Exception as exc:
                raise ProviderError(
                    message="Common Crawl request failed", retryable=True
                ) from exc
            if resp.status_code == 404:
                continue
            if resp.status_code != 200:
                raise ProviderError(
                    message="Common Crawl unexpected response", retryable=False
                )
            content = (
                resp.content
                if isinstance(resp.content, str)
                else resp.content.decode("utf-8", errors="replace")
            )
            urls_found = []
            for line in content.strip().splitlines():
                try:
                    rec = json.loads(line)
                    found_url = str(rec.get("url", "")).strip()
                    if found_url and found_url not in seen:
                        seen.add(found_url)
                        urls_found.append(found_url)
                except Exception:
                    pass
            for u in urls_found[:10]:
                findings.append(
                    dict(
                        provider=self.name,
                        category="web_content",
                        title=f"CommonCrawl URL: {u[:80]}",
                        description=f"URL found in Common Crawl index for {val}: {u}",
                        entity_type="url",
                        entity_value=u,
                        confidence=0.65,
                        tags=["commoncrawl", "web", "passive"],
                    )
                )
            if urls_found:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Common Crawl URLs for {val}",
                        raw={"count": len(urls_found)},
                        confidence=0.65,
                    )
                )
        return findings
