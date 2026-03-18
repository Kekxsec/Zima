# backend/app/providers/social/snov/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_snov.py (MIT licensed)
import json
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class SnovProvider(BaseProviderClient):
    name = "snov"
    base_url = "https://api.snov.io/v1"

    def __init__(
        self, client_id: str = "", client_secret: str = "", timeout_seconds: int = 15
    ):
        self._client_id = client_id
        self._client_secret = client_secret
        self._timeout_seconds = timeout_seconds

    async def _get_token(self, client_id: str, client_secret: str) -> str:
        payload = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            }
        )
        try:
            resp = await self._post(
                f"{self.base_url}/oauth/access_token",
                data=payload,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=self._timeout_seconds,
            )
        except Exception as exc:
            raise ProviderError(message="Snov.io auth failed", retryable=True) from exc
        if resp.status_code in {401, 403}:
            raise ProviderError(message="Snov.io rejected credentials", retryable=False)
        try:
            data = json.loads(resp.content)
            return data.get("access_token", "")
        except Exception:
            return ""

    async def search_emails(
        self, *, domain: str | None = None, email: str | None = None
    ) -> list[dict[str, Any]]:
        client_id = str(self._client_id).strip()
        client_secret = str(self._client_secret).strip()
        if not client_id or not client_secret:
            raise ProviderError(
                message="Snov.io client ID and secret are required", retryable=False
            )
        token = await self._get_token(client_id, client_secret)
        if not token:
            raise ProviderError(
                message="Snov.io could not obtain access token", retryable=False
            )
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        for _entity_type, _value in _inputs:
            if _entity_type != "domain":
                continue
            val = _value.strip()
            url = f"{self.base_url}/get-domain-emails?domain={urllib.parse.quote(val)}&type=all&limit=10&lastId=0&access_token={token}"
            data = self._fetch(url)
            emails = data.get("emails", []) if isinstance(data, dict) else []
            if not isinstance(emails, list):
                continue
            for item in emails[:10]:
                if not isinstance(item, dict):
                    continue
                email = str(item.get("email", "")).strip()
                if not email or email in seen:
                    continue
                seen.add(email)
                findings.append(
                    dict(
                        provider=self.name,
                        category="email_address",
                        title=f"Snov: {email}",
                        description=f"Email found for {val} via Snov.io: {email}",
                        entity_type="email",
                        entity_value=email,
                        confidence=0.72,
                        tags=["snov", "email", "passive"],
                    )
                )
            if emails:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Snov.io emails for {val}",
                        raw={"count": len(emails)},
                        confidence=0.72,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Snov", timeout=self._timeout_seconds)
