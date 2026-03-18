# backend/app/providers/social/gleif/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_gleif.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class GleifProvider(BaseProviderClient):
    name = "gleif"
    base_url = "https://api.gleif.org/api/v1"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def lookup_company(
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
            q = val.split(".")[0] if _entity_type == "domain" else val
            url = f"{self.base_url}/fuzzycompletions?{urllib.parse.urlencode({'field': 'entity.legalName', 'q': q})}"
            data = self._fetch(url)
            items = data.get("data", []) if isinstance(data, dict) else []
            if not isinstance(items, list):
                continue
            for item in items[:10]:
                if not isinstance(item, dict):
                    continue
                attrs = item.get("attributes", {}) or {}
                name = str(attrs.get("value", "")).strip()
                lei = str(
                    item.get("relationships", {})
                    .get("lei-records", {})
                    .get("data", {})
                    .get("id", "")
                ).strip()
                if not name or name in seen:
                    continue
                seen.add(name)
                findings.append(
                    dict(
                        provider=self.name,
                        category="corporate_info",
                        title=f"GLEIF: {name}",
                        description=f"Legal entity found for {val}: {name}"
                        + (f" (LEI: {lei})" if lei else ""),
                        entity_type="human_name",
                        entity_value=name,
                        confidence=0.72,
                        tags=["gleif", "lei", "corporate", "passive"],
                    )
                )
            if items:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"GLEIF results for {val}",
                        raw={"count": len(items)},
                        confidence=0.72,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Gleif", timeout=self._timeout_seconds)
