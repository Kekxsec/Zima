# backend/app/providers/threat_intel/intelx/client.py
"""IntelX — dark web and data leak intelligence REST API client.

Two-phase search:
  1. POST /intelligent/search   → returns search ID
  2. GET  /intelligent/search/result?id=<id>&limit=<n>  → results

API docs: https://intelx.io/api
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import ProviderError, ProviderRateLimitError

_BASE_URL = "https://2.intelx.io"
_SEARCH_ENDPOINT = "/intelligent/search"
_RESULT_ENDPOINT = "/intelligent/search/result"
_DEFAULT_LIMIT = 10
_POLL_INTERVAL_SECONDS = 2
_MAX_POLL_ATTEMPTS = 10
_TIMEOUT_SECONDS = 30


class IntelXProvider(BaseProviderClient):
    """IntelX dark web / data leak search provider.

    Requires an IntelX API key (https://intelx.io — free tier available).
    """

    name = "intelx"

    def __init__(self, api_key: str, timeout_seconds: int = _TIMEOUT_SECONDS) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self._api_key = api_key
        self._headers = {
            "x-key": api_key,
            "Content-Type": "application/json",
        }

    async def search(
        self,
        term: str,
        limit: int = _DEFAULT_LIMIT,
    ) -> list[dict[str, Any]]:
        """Search IntelX for *term* (email, username, domain, etc.).

        Returns a list of normalised finding dicts, one per result record.
        """
        async with httpx.AsyncClient(
            base_url=_BASE_URL,
            timeout=self._timeout_seconds,
        ) as client:
            search_id = await self._start_search(client, term)
            records = await self._poll_results(client, search_id, limit)

        findings: list[dict[str, Any]] = []
        for record in records:
            findings.append(
                dict(
                    provider=self.name,
                    category="darkweb_identity",
                    title=self._record_title(record),
                    description=(
                        f"IntelX found a record matching '{term}' "
                        f"in source: {record.get('storageid', 'unknown')}"
                    ),
                    entity_type="email",
                    entity_value=term,
                    tags=["intelx", "dark_web", "data_leak"],
                    raw=record,
                )
            )

        return findings

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _start_search(self, client: httpx.AsyncClient, term: str) -> str:
        payload = {
            "term": term,
            "buckets": [],
            "lookuplevel": 0,
            "maxresults": _DEFAULT_LIMIT,
            "timeout": 0,
            "datefrom": "",
            "dateto": "",
            "sort": 4,
            "media": 0,
            "terminate": [],
        }
        try:
            response = await client.post(
                _SEARCH_ENDPOINT,
                json=payload,
                headers=self._headers,
            )
        except httpx.TimeoutException as exc:
            raise ProviderError(
                message=f"IntelX search request timed out for '{term}'",
                retryable=True,
            ) from exc
        except httpx.RequestError as exc:
            raise ProviderError(
                message=f"IntelX network error: {exc}",
                retryable=True,
            ) from exc

        if response.status_code == 429:
            raise ProviderRateLimitError(
                message="IntelX rate limit reached",
                retryable=True,
                retry_after=60,
            )
        if response.status_code == 401:
            raise ProviderError(
                message="IntelX API key is invalid or missing",
                retryable=False,
            )
        if response.status_code != 200:
            raise ProviderError(
                message=f"IntelX search failed: HTTP {response.status_code}",
                retryable=False,
            )

        data = response.json()
        search_id: str = data.get("id", "")
        if not search_id:
            raise ProviderError(
                message="IntelX returned no search ID",
                retryable=False,
            )
        return search_id

    async def _poll_results(
        self,
        client: httpx.AsyncClient,
        search_id: str,
        limit: int,
    ) -> list[dict[str, Any]]:
        for _attempt in range(_MAX_POLL_ATTEMPTS):
            await asyncio.sleep(_POLL_INTERVAL_SECONDS)
            try:
                response = await client.get(
                    _RESULT_ENDPOINT,
                    params={"id": search_id, "limit": limit},
                    headers=self._headers,
                )
            except httpx.RequestError as exc:
                raise ProviderError(
                    message=f"IntelX result poll error: {exc}",
                    retryable=True,
                ) from exc

            if response.status_code == 404:
                # Search still pending — continue polling.
                continue
            if response.status_code != 200:
                raise ProviderError(
                    message=f"IntelX result poll failed: HTTP {response.status_code}",
                    retryable=False,
                )

            data = response.json()
            status: int = data.get("status", -1)
            records: list[dict[str, Any]] = data.get("records", []) or []

            # status 1 = results available; 2 = all done
            if status in (1, 2) or records:
                return records

        # Timed out waiting for results — return whatever was collected.
        return []

    @staticmethod
    def _record_title(record: dict[str, Any]) -> str:
        name = record.get("name") or record.get("storageid") or "IntelX record"
        return f"Dark web record: {name}"
