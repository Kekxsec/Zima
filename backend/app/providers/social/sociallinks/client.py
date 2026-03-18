# backend/app/providers/social/sociallinks/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_sociallinks.py (MIT licensed)
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class SociallinksProvider(BaseProviderClient):
    name = "sociallinks"
    base_url = "https://osint.rest/api"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search_social(
        self,
        *,
        email: str | None = None,
        phone_number: str | None = None,
        username: str | None = None,
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="SocialLinks API key is required", retryable=False
            )
        headers = {"token": api_key, "Accept": "application/json"}
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if email is not None:
            _inputs.append(("email", email))
        if phone_number is not None:
            _inputs.append(("phone_number", phone_number))
        if username is not None:
            _inputs.append(("username", username))
        for _entity_type, _value in _inputs:
            val = _value.strip()
            if _entity_type == "email":
                endpoint = f"/email/{val}"
            elif _entity_type == "username":
                endpoint = f"/username/{val}"
            elif _entity_type == "phone":
                endpoint = f"/phone/{val}"
            else:
                return findings
            url = f"{self.base_url}{endpoint}"
            data = self._fetch(url, headers)
            if not isinstance(data, dict):
                continue
            profiles = data.get("profiles", []) or []
            if not isinstance(profiles, list):
                continue
            for profile in profiles[:10]:
                if not isinstance(profile, dict):
                    continue
                platform = str(profile.get("site", "")).strip()
                username = str(
                    profile.get("url", "") or profile.get("username", "")
                ).strip()
                if platform and username:
                    findings.append(
                        dict(
                            provider=self.name,
                            category="social_media",
                            title=f"SocialLinks {platform}: {val}",
                            description=f"Social profile found for {val} on {platform}: {username}",
                            entity_type=_entity_type,
                            entity_value=val,
                            confidence=0.75,
                            tags=["sociallinks", "social_media", "passive"],
                        )
                    )
            if profiles:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"SocialLinks profiles for {val}",
                        raw={"count": len(profiles)},
                        confidence=0.75,
                    )
                )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Sociallinks", headers=headers, timeout=self._timeout_seconds
        )
