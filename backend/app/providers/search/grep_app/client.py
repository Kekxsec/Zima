# backend/app/providers/search/grep_app/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.LOW
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_grep_app.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class GrepAppProvider(BaseProviderClient):
    name = "grep_app"
    base_url = "https://grep.app/api/search"

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
            params = urllib.parse.urlencode({"q": val, "page": "1"})
            url = f"{self.base_url}?{params}"
            data = self._fetch(url)
            hits = (
                data.get("hits", {}).get("hits", []) if isinstance(data, dict) else []
            )
            if not isinstance(hits, list):
                continue
            for hit in hits[:10]:
                if not isinstance(hit, dict):
                    continue
                repo = str(
                    hit.get("repo", {}).get("raw", "")
                    if isinstance(hit.get("repo"), dict)
                    else ""
                ).strip()
                path = str(
                    hit.get("path", {}).get("raw", "")
                    if isinstance(hit.get("path"), dict)
                    else ""
                ).strip()
                key = f"{repo}/{path}"
                if not repo or key in seen:
                    continue
                seen.add(key)
                findings.append(
                    dict(
                        provider=self.name,
                        category="code_reference",
                        title=f"grep.app: {repo}",
                        description=f"Code reference to {val} found in: {repo}/{path}",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.65,
                        tags=["grep_app", "code", "passive"],
                    )
                )
            if hits:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"grep.app results for {val}",
                        raw={"count": len(hits)},
                        confidence=0.65,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="GrepApp", timeout=self._timeout_seconds)
