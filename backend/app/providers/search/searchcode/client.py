# backend/app/providers/search/searchcode/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.LOW
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_searchcode.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class SearchcodeProvider(BaseProviderClient):
    name = "searchcode"
    base_url = "https://searchcode.com/api/codesearch_I"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def search_code(
        self, *, domain: str | None = None, email: str | None = None
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "email"}:
                continue
            val = _value.strip()
            url = f"{self.base_url}/?{urllib.parse.urlencode({'q': val, 'per_page': '10'})}"
            data = self._fetch(url)
            results = data.get("results", []) if isinstance(data, dict) else []
            if not isinstance(results, list):
                continue
            for item in results[:10]:
                if not isinstance(item, dict):
                    continue
                repo = str(item.get("repo", "")).strip()
                filename = str(item.get("filename", "")).strip()
                key = f"{repo}/{filename}"
                if not repo or key in seen:
                    continue
                seen.add(key)
                findings.append(
                    dict(
                        provider=self.name,
                        category="code_reference",
                        title=f"Searchcode: {repo}",
                        description=f"Code reference to {val} in {repo}/{filename}",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.65,
                        tags=["searchcode", "code", "passive"],
                    )
                )
            if results:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Searchcode results for {val}",
                        raw={"count": len(results)},
                        confidence=0.65,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Searchcode", timeout=self._timeout_seconds)
