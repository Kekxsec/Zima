# backend/app/providers/social/skymem/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_skymem.py (MIT licensed)
import re
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class SkymemProvider(BaseProviderClient):
    name = "skymem"
    base_url = "http://www.skymem.info"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def search_emails(
        self, *, domain: str | None = None, email: str | None = None
    ) -> list[dict[str, Any]]:
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
            url = f"{self.base_url}/srp?q={val}"
            try:
                resp = await self._get(url, timeout=self._timeout_seconds)
            except Exception as exc:
                raise ProviderError(
                    message="Skymem request failed", retryable=True
                ) from exc
            if resp.status_code == 429:
                raise ProviderError(message="Skymem rate limited", retryable=True)
            if resp.status_code != 200:
                raise ProviderError(
                    message="Skymem unexpected response", retryable=False
                )
            content = (
                resp.content
                if isinstance(resp.content, str)
                else resp.content.decode("utf-8", errors="replace")
            )
            # Extract emails from response
            emails = re.findall(
                r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", content
            )
            domain_emails = [
                e for e in emails if val.lower() in e.lower() and e not in seen
            ][:10]
            for email in domain_emails:
                seen.add(email)
                findings.append(
                    dict(
                        provider=self.name,
                        category="email_address",
                        title=f"Skymem: {email}",
                        description=f"Email found for {val} on Skymem: {email}",
                        entity_type="email",
                        entity_value=email,
                        confidence=0.70,
                        tags=["skymem", "email", "passive"],
                    )
                )
            if domain_emails:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Skymem emails for {val}",
                        raw={"count": len(domain_emails)},
                        confidence=0.70,
                    )
                )
        return findings
