# backend/app/providers/darkweb/darksearch/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity = FindingSeverity.HIGH
# STRIPPED: severity = FindingSeverity.MEDIUM
# --- End migration notes ---
import urllib.parse
from typing import Any

_SUPPORTED_ENTITY_TYPES = {
    "email",
    "domain",
    "username",
    "human_name",
    "phone",
}

_DEFAULT_MAX_PAGES = 2
_HARD_MAX_PAGES = 5


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class DarkSearchProvider(BaseProviderClient):
    """DarkSearch.io - dark web search engine API."""

    name = "darksearch"
    base_url = "https://darksearch.io/api"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def search_darkweb(
        self,
        *,
        domain: str | None = None,
        email: str | None = None,
        name: str | None = None,
        phone_number: str | None = None,
        username: str | None = None,
    ) -> list[dict[str, Any]]:
        raw_max = _DEFAULT_MAX_PAGES
        try:
            max_pages = max(1, min(int(raw_max), _HARD_MAX_PAGES))
        except (TypeError, ValueError):
            max_pages = _DEFAULT_MAX_PAGES

        findings: list = []
        evidence: list = []

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        if name is not None:
            _inputs.append(("name", name))
        if phone_number is not None:
            _inputs.append(("phone_number", phone_number))
        if username is not None:
            _inputs.append(("username", username))
        for _entity_type, _value in _inputs:
            if _entity_type not in _SUPPORTED_ENTITY_TYPES:
                continue

            query = _value.strip()
            all_results: list = []

            for page in range(1, max_pages + 1):
                params = urllib.parse.urlencode({"query": query, "page": page})
                url = f"{self.base_url}/search?{params}"

                try:
                    resp = await self._get(url, timeout=self._timeout_seconds)
                except Exception as exc:
                    raise ProviderError(
                        message="DarkSearch request failed",
                        retryable=True,
                    ) from exc

                if resp.status_code == 429:
                    # Rate limited — stop paginating gracefully
                    break

                self._check_status_errors(resp, "DarkSearch")

                if resp.status_code == 404 or not resp.content.strip():
                    break

                if resp.status_code != 200:
                    break

                data = self._parse_json(resp, "DarkSearch")
                page_data = data.get("data") or []
                if not isinstance(page_data, list):
                    break

                all_results.extend(page_data)
                data.get("total", 0)
                last_page = data.get("last_page", 1)

                if page >= last_page:
                    break

            total_found = len(all_results)

            for result in all_results:
                link = str(result.get("link", "")).strip()
                title = str(result.get("title", "")).strip()
                snippet = str(result.get("description", "")).strip()

                # Determine severity: HIGH if entity value appears directly in the snippet
                if query.lower() in snippet.lower():
                    pass  # severity was stripped by migration
                else:
                    pass  # severity was stripped by migration

                desc_parts = [f"Dark web mention of '{query}' found."]
                if title:
                    desc_parts.append(f"Page title: {title}.")
                if snippet:
                    desc_parts.append(f"Snippet: {snippet[:300]}")
                if link:
                    desc_parts.append(f"URL: {link}")

                findings.append(
                    dict(
                        provider=self.name,
                        category="dark_web_exposure",
                        title=f"Dark web mention: {query}",
                        description=" ".join(desc_parts),
                        entity_type=_entity_type,
                        entity_value=_value,
                        confidence=0.60,
                        tags=["dark_web", "onion", "darksearch", "passive"],
                    )
                )

            if all_results:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"DarkSearch results for '{query}'",
                        raw={"query": query, "total_retrieved": total_found},
                        confidence=0.60,
                    )
                )

        return findings
