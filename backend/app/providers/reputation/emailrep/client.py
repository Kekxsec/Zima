# backend/app/providers/reputation/emailrep/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_emailrep.py (MIT licensed)
from backend.app.providers.base.client import BaseProviderClient


class EmailrepProvider(BaseProviderClient):
    name = "emailrep"
    base_url = "https://emailrep.io"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_reputation(self, email: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        headers: dict = {"Accept": "application/json"}
        if api_key:
            headers["Key"] = api_key
        findings, evidence = [], []
        val = email.strip()
        url = f"{self.base_url}/{val}"
        data = self._fetch(url, headers)
        if not isinstance(data, dict):
            return findings
        reputation = str(data.get("reputation", "")).strip()
        suspicious = data.get("suspicious", False)
        references = data.get("references", 0)
        if reputation or suspicious:
            sev = "removed_severity" if suspicious else "removed_severity"
            findings.append(
                dict(
                    provider=self.name,
                    category="email_reputation",
                    title=f"EmailRep: {val}",
                    description=f"Email reputation for {val}: {reputation}"
                    + (" (suspicious)" if suspicious else "")
                    + (f", {references} references" if references else ""),
                    severity=sev,
                    entity_type="email",
                    entity_value=val,
                    confidence=0.78,
                    tags=["emailrep", "email", "reputation", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"EmailRep data for {val}",
                    raw={
                        "reputation": reputation,
                        "suspicious": suspicious,
                        "references": references,
                    },
                    confidence=0.78,
                )
            )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Emailrep", headers=headers, timeout=self._timeout_seconds
        )
