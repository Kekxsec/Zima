# backend/app/providers/social/wikipediaedits/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_wikipediaedits.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class WikipediaeditsProvider(BaseProviderClient):
    name = "wikipediaedits"
    base_url = "https://en.wikipedia.org/w/api.php"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def search_social(
        self, *, ip_address: str | None = None, username: str | None = None
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        if username is not None:
            _inputs.append(("username", username))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"ip_address", "username"}:
                continue
            val = _value.strip()
            params = urllib.parse.urlencode(
                {
                    "action": "query",
                    "list": "usercontribs",
                    "ucuser": val,
                    "uclimit": "10",
                    "format": "json",
                }
            )
            url = f"{self.base_url}?{params}"
            data = self._fetch(url)
            contribs = data.get("query", {}).get("usercontribs", [])
            if not isinstance(contribs, list):
                continue
            if contribs:
                pages = list(
                    {str(c.get("title", "")) for c in contribs if c.get("title")}
                )[:5]
                findings.append(
                    dict(
                        provider=self.name,
                        category="social_media",
                        title=f"Wikipedia edits found for {val}",
                        description=f"{val} has {len(contribs)} Wikipedia contributions including: {', '.join(pages[:3])}",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.80,
                        tags=["wikipedia", "social_media", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Wikipedia contributions for {val}",
                        raw={"count": len(contribs), "pages": pages},
                        confidence=0.80,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(
            url, label="Wikipediaedits", timeout=self._timeout_seconds
        )
