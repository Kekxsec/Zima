# backend/app/providers/social/slideshare/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_slideshare.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class SlideshareProvider(BaseProviderClient):
    name = "slideshare"
    base_url = "https://www.slideshare.net/api/oembed/2"

    def __init__(
        self, api_key: str = "", api_secret: str = "", timeout_seconds: int = 15
    ):
        self._api_key = api_key
        self._api_secret = api_secret
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
            if _entity_type not in {"human_name", "username"}:
                continue
            val = _value.strip()
            username = val.replace(" ", "").lower()
            url = f"https://www.slideshare.net/{urllib.parse.quote(username)}"
            try:
                resp = await self._get(url, timeout=self._timeout_seconds)
            except Exception as exc:
                raise ProviderError(
                    message="SlideShare request failed", retryable=True
                ) from exc
            if resp.status_code == 404:
                continue
            if resp.status_code == 429:
                raise ProviderError(message="SlideShare rate limited", retryable=True)
            if resp.status_code != 200:
                continue
            content = (
                resp.content
                if isinstance(resp.content, str)
                else resp.content.decode("utf-8", errors="replace")
            )
            if username.lower() in content.lower() and "slideshare" in content.lower():
                findings.append(
                    dict(
                        provider=self.name,
                        category="social_media",
                        title=f"SlideShare: {val}",
                        description=f"SlideShare profile found for {val}: {url}",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.65,
                        tags=["slideshare", "social_media", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"SlideShare profile for {val}",
                        raw={"url": url},
                        confidence=0.65,
                    )
                )
        return findings
