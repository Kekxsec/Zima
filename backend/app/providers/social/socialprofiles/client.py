# backend/app/providers/social/socialprofiles/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_socialprofiles.py (MIT licensed)
import urllib.parse
from typing import Any

_SOCIAL_SITES = [
    "twitter.com",
    "linkedin.com",
    "facebook.com",
    "instagram.com",
    "github.com",
    "reddit.com",
]


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class SocialprofilesProvider(BaseProviderClient):
    name = "socialprofiles"
    base_url = "https://www.googleapis.com/customsearch/v1"

    def __init__(self, api_key: str = "", cse_id: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._cse_id = cse_id
        self._timeout_seconds = timeout_seconds

    async def search_social(
        self, *, name: str | None = None, username: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        cse_id = str(self._cse_id).strip()
        if not api_key or not cse_id:
            raise ProviderError(
                message="Google API key and CSE ID are required", retryable=False
            )
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if name is not None:
            _inputs.append(("name", name))
        if username is not None:
            _inputs.append(("username", username))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"human_name", "username"}:
                continue
            val = _value.strip()
            for site in _SOCIAL_SITES[:3]:
                query = f'site:{site} "{val}"'
                params = urllib.parse.urlencode(
                    {"key": api_key, "cx": cse_id, "q": query, "num": "5"}
                )
                url = f"{self.base_url}?{params}"
                data = self._fetch(url)
                items = data.get("items", []) if isinstance(data, dict) else []
                for item in items[:3]:
                    if not isinstance(item, dict):
                        continue
                    link = str(item.get("link", "")).strip()
                    if not link or link in seen:
                        continue
                    seen.add(link)
                    findings.append(
                        dict(
                            provider=self.name,
                            category="social_media",
                            title=f"Social profile: {site}",
                            description=f"Social profile for {val} on {site}: {link}",
                            entity_type=_entity_type,
                            entity_value=val,
                            confidence=0.65,
                            tags=["socialprofiles", "social_media", "passive"],
                        )
                    )
                if items:
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"Social profile search for {val} on {site}",
                            raw={"count": len(items)},
                            confidence=0.65,
                        )
                    )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(
            url, label="Socialprofiles", timeout=self._timeout_seconds
        )
