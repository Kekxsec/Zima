# backend/app/providers/social/flickr/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_flickr.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class FlickrProvider(BaseProviderClient):
    name = "flickr"
    base_url = "https://api.flickr.com/services/rest/"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search_social(
        self,
        *,
        domain: str | None = None,
        name: str | None = None,
        username: str | None = None,
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(message="Flickr API key is required", retryable=False)
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if name is not None:
            _inputs.append(("name", name))
        if username is not None:
            _inputs.append(("username", username))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "human_name", "username"}:
                continue
            val = _value.strip()
            params = {
                "method": "flickr.people.findByUsername",
                "api_key": api_key,
                "username": val,
                "format": "json",
                "nojsoncallback": "1",
            }
            url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
            data = self._fetch(url)
            if not isinstance(data, dict):
                continue
            user = data.get("user", {})
            if not isinstance(user, dict):
                continue
            user_id = str(user.get("id", "")).strip()
            nsid = str(user.get("nsid", "")).strip()
            if user_id and user_id not in seen:
                seen.add(user_id)
                findings.append(
                    dict(
                        provider=self.name,
                        category="social_media",
                        title=f"Flickr account: {val}",
                        description=f"Flickr account found for {val} (NSID: {nsid or user_id})",
                        entity_type="username",
                        entity_value=val,
                        confidence=0.75,
                        tags=["flickr", "social_media", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Flickr account for {val}",
                        raw={"nsid": nsid, "user_id": user_id},
                        confidence=0.75,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Flickr", timeout=self._timeout_seconds)
