# backend/app/providers/search/crossref/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_crossref.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class CrossrefProvider(BaseProviderClient):
    name = "crossref"
    base_url = "https://api.crossref.org/works"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def search_publications(
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
            url = f"{self.base_url}?query={urllib.parse.quote(val)}&rows=5"
            data = self._fetch(url)
            items = (
                data.get("message", {}).get("items", [])
                if isinstance(data, dict)
                else []
            )
            if not isinstance(items, list):
                continue
            for item in items[:5]:
                if not isinstance(item, dict):
                    continue
                title_list = item.get("title", [])
                title = str(title_list[0] if title_list else "").strip()
                doi = str(item.get("DOI", "")).strip()
                if not title or title in seen:
                    continue
                seen.add(title)
                findings.append(
                    dict(
                        provider=self.name,
                        category="academic",
                        title=f"Crossref: {title[:60]}",
                        description=f"Academic publication related to {val}: {title}"
                        + (f" (DOI: {doi})" if doi else ""),
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.55,
                        tags=["crossref", "academic", "passive"],
                    )
                )
            if items:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Crossref publications for {val}",
                        raw={"count": len(items)},
                        confidence=0.55,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Crossref", timeout=self._timeout_seconds)
