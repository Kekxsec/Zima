# backend/app/providers/social/emailcrawlr/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_emailcrawlr.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class EmailcrawlrProvider(BaseProviderClient):
    name = "emailcrawlr"
    base_url = "https://api.emailcrawlr.com/v2"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        super().__init__(timeout_seconds=timeout_seconds)
        self._api_key = api_key

    async def search_emails(
        self, *, domain: str | None = None, email: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="EmailCrawlr API key is required", retryable=False
            )
        headers = {"Accept": "application/json", "x-api-key": api_key}
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
            url = f"{self.base_url}/domain?{urllib.parse.urlencode({'domain': val})}"
            data = await self._fetch(url, headers)
            emails = data.get("emails", []) if isinstance(data, dict) else []
            if not isinstance(emails, list):
                continue
            for item in emails[:20]:
                if not isinstance(item, dict):
                    continue
                email = str(item.get("value", "")).strip()
                if not email or email in seen:
                    continue
                seen.add(email)
                findings.append(
                    dict(
                        provider=self.name,
                        category="email_address",
                        title=f"EmailCrawlr: {email}",
                        description=f"Email address found for domain {val}: {email}",
                        entity_type="email",
                        entity_value=email,
                        confidence=0.75,
                        tags=["emailcrawlr", "email", "passive"],
                    )
                )
            if emails:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"EmailCrawlr emails for {val}",
                        raw={"count": len(emails)},
                        confidence=0.75,
                    )
                )
        return findings

    async def get_email(self, email: str) -> dict[str, Any]:
        """Fetch rich profile data for a specific email address.

        GET /v2/{email}
        Returns the full JSON body or {} if not found (404).
        Fields: email, personal, domain, verified, linkedin, twitter, name,
                references, job_title, location, numbers.
        """
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="EmailCrawlr API key is required", retryable=False
            )
        headers = {"Accept": "application/json", "x-api-key": api_key}
        url = f"{self.base_url}/{urllib.parse.quote(email.strip(), safe='')}"
        return await self._fetch(url, headers)

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Emailcrawlr", headers=headers, timeout=self._timeout_seconds
        )
