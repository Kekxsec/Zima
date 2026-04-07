# backend/app/providers/social/emailformat/client.py
from __future__ import annotations

import re
from typing import Any

import httpx

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderAuthError,
    ProviderError,
    ProviderRateLimitError,
)

# Matches email addresses in HTML body
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


class EmailformatProvider(BaseProviderClient):
    """emailformat.com — domain email-format scraper.

    Scrapes https://www.email-format.com/d/{domain}/ to discover
    email address patterns and sample addresses for a domain.
    Enrichment-only (no signals). Used by alias_correlation.
    """

    name = "emailformat"
    base_url = "https://www.email-format.com/d"

    def __init__(self, timeout_seconds: int = 15) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    async def get_formats(self, domain: str) -> list[dict[str, Any]]:
        """Scrape email addresses/formats found for the given domain.

        Returns a list of enrichment dicts with keys: email, domain.
        Returns [] on 404 or if no addresses found.
        """
        val = domain.strip().lower()
        url = f"{self.base_url}/{val}/"
        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                resp = await client.get(url)
        except httpx.TimeoutException as exc:
            raise ProviderError(
                message="EmailFormat request timed out", retryable=True
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(
                message="EmailFormat request failed", retryable=True
            ) from exc

        if resp.status_code == 404:
            return []
        if resp.status_code in {401, 403}:
            raise ProviderAuthError("EmailFormat rejected request")
        if resp.status_code == 429:
            raise ProviderRateLimitError("EmailFormat rate limited")
        if resp.status_code >= 500:
            raise ProviderError(
                message=f"EmailFormat upstream error ({resp.status_code})",
                retryable=True,
            )

        content = resp.text
        emails = _EMAIL_RE.findall(content)
        seen: set[str] = set()
        results: list[dict[str, Any]] = []
        for addr in emails:
            if val not in addr or addr in seen:
                continue
            seen.add(addr)
            results.append({"email": addr, "domain": val})
            if len(results) >= 10:
                break
        return results
