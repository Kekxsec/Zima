# backend/app/providers/social/gravatar/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_gravatar.py (MIT licensed)
import hashlib
import json
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class GravatarProvider(BaseProviderClient):
    name = "gravatar"
    base_url = "https://secure.gravatar.com"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def get_gravatar(self, email: str) -> list[dict[str, Any]]:
        findings, evidence = [], []
        val = email.strip().lower()
        email_hash = hashlib.md5(val.encode("utf-8")).hexdigest()
        url = f"{self.base_url}/{email_hash}.json"
        try:
            resp = await self._get(url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="Gravatar request failed", retryable=True
            ) from exc
        if resp.status_code == 404:
            return findings
        if resp.status_code == 429:
            raise ProviderError(message="Gravatar rate limited", retryable=True)
        if resp.status_code != 200:
            raise ProviderError(message="Gravatar unexpected response", retryable=False)
        try:
            data = json.loads(resp.content)
        except Exception:
            return findings
        entry = (
            (data.get("entry") or [{}])[0]
            if isinstance(data.get("entry"), list)
            else {}
        )
        display_name = str(entry.get("displayName", "")).strip()
        profile_url = str(entry.get("profileUrl", "")).strip()
        if display_name or profile_url:
            findings.append(
                dict(
                    provider=self.name,
                    category="social_media",
                    title=f"Gravatar: {val}",
                    description=f"Gravatar profile found for {val}: {display_name or email_hash}",
                    entity_type="email",
                    entity_value=val,
                    confidence=0.80,
                    tags=["gravatar", "social_media", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"Gravatar profile for {val}",
                    raw={"displayName": display_name, "profileUrl": profile_url},
                    confidence=0.80,
                )
            )
        return findings
