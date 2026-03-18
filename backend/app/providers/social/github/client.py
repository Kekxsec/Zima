# backend/app/providers/social/github/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_github.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class GithubProvider(BaseProviderClient):
    name = "github"
    base_url = "https://api.github.com"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search_profiles(
        self,
        *,
        domain: str | None = None,
        email: str | None = None,
        username: str | None = None,
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        headers = {"Accept": "application/vnd.github.v3+json"}
        if api_key:
            headers["Authorization"] = f"token {api_key}"
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        if username is not None:
            _inputs.append(("username", username))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "email", "username"}:
                continue
            q = _value.strip()
            if _entity_type == "username":
                params = urllib.parse.urlencode(
                    {"q": q, "type": "users", "per_page": "10"}
                )
            else:
                params = urllib.parse.urlencode(
                    {"q": q, "type": "repositories", "per_page": "10"}
                )
            search_type = "users" if _entity_type == "username" else "repositories"
            url = f"{self.base_url}/search/{search_type}?{params}"
            data = self._fetch(url, headers)
            items = data.get("items", [])
            if not isinstance(items, list):
                continue
            for item in items[:10]:
                val = str(item.get("login", "") or item.get("full_name", "")).strip()
                if not val or val in seen:
                    continue
                seen.add(val)
                findings.append(
                    dict(
                        provider=self.name,
                        category="social_media",
                        title=f"GitHub: {val}",
                        description=f"GitHub profile/repository found for {q}: {val}",
                        entity_type="username",
                        entity_value=val,
                        confidence=0.70,
                        tags=["github", "passive"],
                    )
                )
            if items:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"GitHub search for {q}",
                        raw={"count": len(items)},
                        confidence=0.70,
                    )
                )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        try:
            resp = await self._get(url, headers=headers, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="Github request failed",
                retryable=True,
            ) from exc
        if resp.status_code == 422:
            raise ProviderError(
                message="GitHub query validation failed", retryable=False
            )
        self._check_status_errors(resp, "Github")
        return self._parse_json(resp, "Github")
