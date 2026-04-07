# backend/app/providers/cloud/chrome_web_store_api/client.py
from __future__ import annotations

import re
from typing import Any

import httpx

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import ProviderError, ProviderRateLimitError

# Regex to extract name from CWS detail page <title> tag
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
# Strip " - Chrome Web Store" suffix
_TITLE_SUFFIX_RE = re.compile(r"\s*[-–]\s*Chrome Web Store\s*$", re.IGNORECASE)


class ChromeWebStoreApiProvider(BaseProviderClient):
    """Unofficial Chrome Web Store metadata scraper.

    Scrapes the CWS detail page to retrieve basic extension metadata.
    There is no public official metadata API — this uses the publicly
    accessible detail page. Fragile by nature; treat results as enrichment
    only and degrade gracefully on failure.

    Enrichment-only — does NOT emit signals directly.
    """

    name = "chrome_web_store_api"
    _DETAIL_URL = "https://chromewebstore.google.com/detail/{extension_id}"

    def __init__(self, timeout_seconds: int = 15) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    async def get_extension(self, extension_id: str) -> dict[str, Any] | None:
        """Fetch basic metadata for a Chrome extension by ID.

        Returns an enrichment dict with keys: id, name, store_url.
        Returns None on 404 or fetch failure.
        Fields beyond `name` require deeper scraping and are omitted in
        this MVP implementation.
        """
        ext_id = extension_id.strip()
        if not ext_id:
            return None

        url = self._DETAIL_URL.format(extension_id=ext_id)
        try:
            async with httpx.AsyncClient(
                timeout=self._timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; ZimaBot/1.0)"},
            ) as client:
                resp = await client.get(url)
        except httpx.TimeoutException as exc:
            raise ProviderError(
                message="Chrome Web Store request timed out", retryable=True
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(
                message="Chrome Web Store request failed", retryable=True
            ) from exc

        if resp.status_code == 404:
            return None
        if resp.status_code == 429:
            raise ProviderRateLimitError("Chrome Web Store rate limited")
        if resp.status_code >= 400:
            return None

        name: str | None = None
        title_match = _TITLE_RE.search(resp.text)
        if title_match:
            raw_title = title_match.group(1).strip()
            name = _TITLE_SUFFIX_RE.sub("", raw_title).strip() or None

        return {
            "id": ext_id,
            "name": name,
            "store_url": url,
        }
