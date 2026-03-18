# backend/app/providers/social/venmo/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_venmo.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class VenmoProvider(BaseProviderClient):
    name = "venmo"
    base_url = "https://venmo.com/api/v5/users"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def search_social(
        self, *, name: str | None = None, username: str | None = None
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if name is not None:
            _inputs.append(("name", name))
        if username is not None:
            _inputs.append(("username", username))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"username", "human_name"}:
                continue
            val = _value.strip()
            params = urllib.parse.urlencode({"query": val, "limit": "5"})
            url = f"{self.base_url}?{params}"
            data = self._fetch(url)
            if not isinstance(data, dict):
                continue
            items = data.get("data", []) or []
            if not isinstance(items, list):
                continue
            for item in items[:5]:
                if not isinstance(item, dict):
                    continue
                username = str(item.get("username", "")).strip()
                display_name = str(item.get("display_name", "")).strip()
                if username or display_name:
                    findings.append(
                        dict(
                            provider=self.name,
                            category="social_media",
                            title=f"Venmo: {username or display_name}",
                            description=f"Venmo user matching {val}: {display_name}"
                            + (f" (@{username})" if username else ""),
                            entity_type="username",
                            entity_value=username or display_name,
                            confidence=0.65,
                            tags=["venmo", "social_media", "passive"],
                        )
                    )
            if items:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Venmo search for {val}",
                        raw={"count": len(items)},
                        confidence=0.65,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Venmo", timeout=self._timeout_seconds)
