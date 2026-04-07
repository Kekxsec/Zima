# backend/app/providers/social/gravatar/client.py
from __future__ import annotations

import hashlib
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class GravatarProvider(BaseProviderClient):
    """Gravatar v3 profile lookup.

    Uses SHA-256 hash of the email address.
    Auth is optional: unauthenticated allows 100 req/h; with Bearer key 1000 req/h.
    Enrichment-only — does not emit signals directly.
    """

    name = "gravatar"
    base_url = "https://api.gravatar.com/v3"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self._api_key = api_key

    async def lookup(self, email: str) -> dict[str, Any] | None:
        """Fetch the Gravatar v3 profile for an email address.

        Returns an enrichment dict on 200, or None if no profile exists (404).
        Raises ProviderError on auth failure, rate-limit, or upstream error.
        """
        sha256_hash = hashlib.sha256(email.strip().lower().encode()).hexdigest()
        url = f"{self.base_url}/profiles/{sha256_hash}"
        headers: dict[str, str] = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        data = await self._get(url, label="Gravatar", headers=headers)
        if not data:
            return None

        return {
            "hash": sha256_hash,
            "display_name": data.get("display_name"),
            "profile_url": data.get("profile_url"),
            "avatar_url": data.get("avatar_url"),
            "location": data.get("location"),
            "description": data.get("description"),
            "job_title": data.get("job_title"),
            "company": data.get("company"),
            "verified_accounts": data.get("verified_accounts", []),
            "links": data.get("links", []),
            "raw": data,
        }
