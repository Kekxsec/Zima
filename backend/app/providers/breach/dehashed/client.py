# backend/app/providers/breach/dehashed/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_dehashed.py (MIT licensed)
import base64
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class DehashedProvider(BaseProviderClient):
    name = "dehashed"
    base_url = "https://api.dehashed.com/search"

    def __init__(
        self, api_email: str = "", api_key: str = "", timeout_seconds: int = 15
    ):
        self._api_email = api_email
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search_breaches(
        self, *, domain: str | None = None, email: str | None = None
    ) -> list[dict[str, Any]]:
        api_email = str(self._api_email).strip()
        api_key = str(self._api_key).strip()
        if not api_email or not api_key:
            raise ProviderError(
                message="DeHashed email and API key are required", retryable=False
            )
        creds = base64.b64encode(f"{api_email}:{api_key}".encode()).decode()
        headers = {"Accept": "application/json", "Authorization": f"Basic {creds}"}
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"email", "domain"}:
                continue
            val = _value.strip()
            query = f'email:"{val}"' if _entity_type == "email" else f'email:"@{val}"'
            url = f"{self.base_url}?query={urllib.parse.quote(query)}&size=5"
            data = self._fetch(url, headers)
            total = data.get("total", 0) if isinstance(data, dict) else 0
            entries = data.get("entries", []) if isinstance(data, dict) else []
            if total and total > 0:
                findings.append(
                    dict(
                        provider=self.name,
                        category="credential_leak",
                        title=f"DeHashed: {val}",
                        description=f"{val} found in {total} DeHashed breach record(s)",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.85,
                        tags=["dehashed", "leak", "breach", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"DeHashed records for {val}",
                        raw={"total": total, "sample_count": len(entries)},
                        confidence=0.85,
                    )
                )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Dehashed", headers=headers, timeout=self._timeout_seconds
        )
