# backend/app/providers/social/hunter/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_hunter.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class HunterProvider(BaseProviderClient):
    name = "hunter"
    base_url = "https://api.hunter.io/v2"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search_emails(
        self, *, domain: str | None = None, email: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="Hunter.io API key is required", retryable=False
            )
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        for _entity_type, _value in _inputs:
            if _entity_type == "domain":
                params = urllib.parse.urlencode(
                    {"domain": _value.strip(), "api_key": api_key}
                )
                url = f"{self.base_url}/domain-search?{params}"
                data = self._fetch(url)
                emails = data.get("data", {}).get("emails", [])
                if not isinstance(emails, list):
                    continue
                for e_obj in emails[:20]:
                    addr = str(e_obj.get("value", "")).strip()
                    if not addr:
                        continue
                    findings.append(
                        dict(
                            provider=self.name,
                            category="email_discovery",
                            title=f"Hunter.io email: {addr}",
                            description=f"Email address {addr} found for domain {_value}",
                            entity_type="email",
                            entity_value=addr,
                            confidence=0.75,
                            tags=["hunter", "email", "passive"],
                        )
                    )
                if emails:
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"Hunter.io domain search for {_value}",
                            raw={"count": len(emails)},
                            confidence=0.75,
                        )
                    )
            elif _entity_type == "email":
                params = urllib.parse.urlencode(
                    {"email": _value.strip(), "api_key": api_key}
                )
                url = f"{self.base_url}/email-verifier?{params}"
                data = self._fetch(url)
                status = str(data.get("data", {}).get("status", "")).strip()
                if status:
                    findings.append(
                        dict(
                            provider=self.name,
                            category="email_verification",
                            title=f"Hunter.io email status: {status}",
                            description=f"Email {_value} verification status: {status}",
                            entity_type="email",
                            entity_value=_value,
                            confidence=0.80,
                            tags=["hunter", "email_verify", "passive"],
                        )
                    )
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"Hunter.io email verification for {_value}",
                            raw={"status": status},
                            confidence=0.80,
                        )
                    )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Hunter", timeout=self._timeout_seconds)
