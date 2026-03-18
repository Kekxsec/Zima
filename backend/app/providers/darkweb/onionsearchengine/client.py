# backend/app/providers/darkweb/onionsearchengine/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_onionsearchengine.py (MIT licensed)
import re
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class OnionsearchengineProvider(BaseProviderClient):
    name = "onionsearchengine"
    base_url = "https://as.onionsearchengine.com"

    def __init__(self, timeout_seconds: int = 30):
        self._timeout_seconds = timeout_seconds

    async def search_darkweb(
        self, *, domain: str | None = None, name: str | None = None
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if name is not None:
            _inputs.append(("name", name))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "human_name"}:
                continue
            val = _value.strip()
            url = f"{self.base_url}/?search={urllib.parse.quote(val)}&submit=1"
            try:
                resp = await self._get(url, timeout=self._timeout_seconds)
            except Exception as exc:
                raise ProviderError(
                    message="OnionSearchEngine request failed", retryable=True
                ) from exc
            if resp.status_code == 429:
                raise ProviderError(
                    message="OnionSearchEngine rate limited", retryable=True
                )
            if resp.status_code != 200:
                raise ProviderError(
                    message="OnionSearchEngine unexpected response", retryable=False
                )
            content = (
                resp.content
                if isinstance(resp.content, str)
                else resp.content.decode("utf-8", errors="replace")
            )
            onion_links = list(
                dict.fromkeys(
                    re.findall(r'https?://[a-z2-7]{16,56}\.onion[^\s"<>]*', content)
                )
            )
            for link in onion_links[:10]:
                if link in seen:
                    continue
                seen.add(link)
                findings.append(
                    dict(
                        provider=self.name,
                        category="dark_web",
                        title=f"Onion: {link[:60]}",
                        description=f"Dark web .onion result for {val}: {link}",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.65,
                        tags=["onionsearchengine", "dark_web", "passive"],
                    )
                )
            if onion_links:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"OnionSearchEngine results for {val}",
                        raw={"count": len(onion_links)},
                        confidence=0.65,
                    )
                )
        return findings
