# backend/app/providers/darkweb/onioncity/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_onioncity.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class OnioncityProvider(BaseProviderClient):
    name = "onioncity"
    base_url = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: str = "", cse_id: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._cse_id = cse_id
        self._timeout_seconds = timeout_seconds

    async def search_darkweb(
        self,
        *,
        domain: str | None = None,
        email: str | None = None,
        name: str | None = None,
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        cse_id = str(self._cse_id).strip()
        if not api_key or not cse_id:
            raise ProviderError(
                message="OnionCity (Google CSE) API key and CSE ID are required",
                retryable=False,
            )
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        if name is not None:
            _inputs.append(("name", name))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "human_name", "email"}:
                continue
            val = _value.strip()
            params = urllib.parse.urlencode(
                {"key": api_key, "cx": cse_id, "q": val, "num": "10"}
            )
            url = f"{self.base_url}?{params}"
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
                        category="dark_web",
                        title=f"Onion City: {title[:60]}",
                        description=f"Dark web result for {val}: {link}",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.65,
                        tags=["onioncity", "dark_web", "passive"],
                    )
                )
            if items:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Onion City search for {val}",
                        raw={"count": len(items)},
                        confidence=0.65,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Onioncity", timeout=self._timeout_seconds)
