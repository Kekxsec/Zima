# backend/app/providers/social/stackoverflow/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_stackoverflow.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class StackoverflowProvider(BaseProviderClient):
    name = "stackoverflow"
    base_url = "https://api.stackexchange.com/2.3"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def search_social(
        self, *, email: str | None = None, username: str | None = None
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if email is not None:
            _inputs.append(("email", email))
        if username is not None:
            _inputs.append(("username", username))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"email", "username"}:
                continue
            val = _value.strip()
            if _entity_type == "email":
                params = urllib.parse.urlencode(
                    {
                        "inname": val.split("@")[0],
                        "site": "stackoverflow",
                        "pagesize": "5",
                    }
                )
            else:
                params = urllib.parse.urlencode(
                    {"inname": val, "site": "stackoverflow", "pagesize": "5"}
                )
            url = f"{self.base_url}/users?{params}"
            data = self._fetch(url)
            items = data.get("items", []) if isinstance(data, dict) else []
            if not isinstance(items, list):
                continue
            for item in items[:5]:
                if not isinstance(item, dict):
                    continue
                display_name = str(item.get("display_name", "")).strip()
                user_id = item.get("user_id")
                reputation = item.get("reputation", 0)
                if display_name:
                    findings.append(
                        dict(
                            provider=self.name,
                            category="social_media",
                            title=f"StackOverflow: {display_name}",
                            description=f"Stack Overflow user matching {val}: {display_name} (rep: {reputation})",
                            entity_type="username",
                            entity_value=display_name,
                            confidence=0.60,
                            tags=["stackoverflow", "social_media", "passive"],
                        )
                    )
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"Stack Overflow match for {val}",
                            raw={
                                "display_name": display_name,
                                "user_id": user_id,
                                "reputation": reputation,
                            },
                            confidence=0.60,
                        )
                    )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(
            url, label="Stackoverflow", timeout=self._timeout_seconds
        )
