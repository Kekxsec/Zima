# backend/app/providers/social/trumail/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity = FindingSeverity.MEDIUM if disposable else FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_trumail.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class TrumailProvider(BaseProviderClient):
    name = "trumail"
    base_url = "https://api.trumail.io/v2/lookups/json"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def validate_email(self, email: str) -> list[dict[str, Any]]:
        findings, evidence = [], []
        val = email.strip()
        url = f"{self.base_url}?address={urllib.parse.quote(val)}"
        data = self._fetch(url)
        if not isinstance(data, dict):
            return findings
        deliverable = data.get("deliverable", False)
        disposable = data.get("disposable", False)
        free = data.get("free", False)
        valid_format = data.get("validFormat", False)
        if valid_format or deliverable is not None:
            desc = f"Email {val}: deliverable={deliverable}, disposable={disposable}, free={free}"
            findings.append(
                dict(
                    provider=self.name,
                    category="email_validation",
                    title=f"Trumail: {val}",
                    description=desc,
                    entity_type="email",
                    entity_value=val,
                    confidence=0.78,
                    tags=["trumail", "email_validation", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"Trumail validation for {val}",
                    raw={
                        "deliverable": deliverable,
                        "disposable": disposable,
                        "free": free,
                        "valid_format": valid_format,
                    },
                    confidence=0.78,
                )
            )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Trumail", timeout=self._timeout_seconds)
