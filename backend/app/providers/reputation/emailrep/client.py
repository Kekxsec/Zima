# backend/app/providers/reputation/emailrep/client.py
from __future__ import annotations

import urllib.parse
from typing import Any

# Adapted from SpiderFoot module: modules/sfp_emailrep.py (MIT licensed)
from backend.app.providers.base.client import BaseProviderClient


class EmailrepProvider(BaseProviderClient):
    name = "emailrep"
    base_url = "https://emailrep.io"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self._api_key = api_key

    async def get_reputation(self, email: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        headers: dict[str, str] = {"Accept": "application/json"}
        if api_key:
            headers["Key"] = api_key
        findings: list[dict[str, Any]] = []
        val = email.strip()
        url = f"{self.base_url}/{urllib.parse.quote(val, safe='')}"
        data = await self._fetch(url, headers)
        if not isinstance(data, dict):
            return findings
        reputation = str(data.get("reputation", "")).strip()
        suspicious = data.get("suspicious", False)
        blacklisted = data.get("blacklisted", False)
        references = data.get("references", 0)
        details = data.get("details", {}) or {}
        spam = details.get("spam", False)
        if reputation or suspicious or blacklisted or spam:
            findings.append(
                dict(
                    provider=self.name,
                    category="email_reputation",
                    title=f"EmailRep: {val}",
                    description=(
                        f"Email reputation for {val}: {reputation}"
                        + (" (suspicious)" if suspicious else "")
                        + (" (blacklisted)" if blacklisted else "")
                        + (f", {references} references" if references else "")
                    ),
                    entity_type="email",
                    entity_value=val,
                    tags=["emailrep", "email", "reputation", "passive"],
                    raw={
                        "reputation": reputation,
                        "suspicious": suspicious,
                        "blacklisted": blacklisted,
                        "spam": spam,
                        "references": references,
                        "profiles": details.get("profiles", []),
                    },
                )
            )
        return findings

    async def _fetch(self, url: str, headers: dict[str, str]) -> dict[str, Any]:
        return await self._get(
            url, label="Emailrep", headers=headers, timeout=self._timeout_seconds
        )
