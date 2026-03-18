# backend/app/providers/social/twitter/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_twitter.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class TwitterProvider(BaseProviderClient):
    name = "twitter"
    base_url = "https://api.twitter.com/2"

    def __init__(self, bearer_token: str = "", timeout_seconds: int = 15):
        self._bearer_token = bearer_token
        self._timeout_seconds = timeout_seconds

    async def search_social(
        self,
        *,
        email: str | None = None,
        name: str | None = None,
        username: str | None = None,
    ) -> list[dict[str, Any]]:
        bearer_token = str(self._bearer_token).strip()
        if not bearer_token:
            raise ProviderError(
                message="Twitter bearer token is required", retryable=False
            )
        headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Accept": "application/json",
        }
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if email is not None:
            _inputs.append(("email", email))
        if name is not None:
            _inputs.append(("name", name))
        if username is not None:
            _inputs.append(("username", username))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"username", "human_name", "email"}:
                continue
            val = _value.strip()
            if _entity_type == "username":
                url = f"{self.base_url}/users/by/username/{urllib.parse.quote(val)}?user.fields=name,description,public_metrics,location"
                data = self._fetch(url, headers)
                user = data.get("data", {}) if isinstance(data, dict) else {}
                if user and isinstance(user, dict):
                    name = str(user.get("name", "")).strip()
                    desc = str(user.get("description", "")).strip()
                    metrics = user.get("public_metrics", {}) or {}
                    findings.append(
                        dict(
                            provider=self.name,
                            category="social_media",
                            title=f"Twitter: @{val}",
                            description=f"Twitter user @{val}: {name}"
                            + (f" — {desc[:100]}" if desc else ""),
                            entity_type="username",
                            entity_value=val,
                            confidence=0.85,
                            tags=["twitter", "social_media", "passive"],
                        )
                    )
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"Twitter profile for @{val}",
                            raw={
                                "name": name,
                                "description": desc[:200],
                                "metrics": metrics,
                            },
                            confidence=0.85,
                        )
                    )
            else:
                # Search by name/email prefix
                query = val.split("@")[0] if "@" in val else val
                params = urllib.parse.urlencode(
                    {
                        "query": query,
                        "max_results": "10",
                        "user.fields": "name,username,description",
                    }
                )
                url = f"{self.base_url}/users/search?{params}"
                data = self._fetch(url, headers)
                users = data.get("data", []) if isinstance(data, dict) else []
                if not isinstance(users, list):
                    return findings
                for user in users[:5]:
                    if not isinstance(user, dict):
                        continue
                    username = str(user.get("username", "")).strip()
                    name = str(user.get("name", "")).strip()
                    if username:
                        findings.append(
                            dict(
                                provider=self.name,
                                category="social_media",
                                title=f"Twitter: @{username}",
                                description=f"Twitter user matching {val}: @{username} ({name})",
                                entity_type="username",
                                entity_value=username,
                                confidence=0.65,
                                tags=["twitter", "social_media", "passive"],
                            )
                        )
                if users:
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"Twitter search for {val}",
                            raw={"count": len(users)},
                            confidence=0.65,
                        )
                    )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Twitter", headers=headers, timeout=self._timeout_seconds
        )
