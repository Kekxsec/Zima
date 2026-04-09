# backend/app/providers/base/client.py
from __future__ import annotations

import json
from abc import ABC
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.app.providers.base.exceptions import (
    ProviderAuthError,
    ProviderRateLimitError,
    ProviderSchemaError,
    ProviderTimeoutError,
    ProviderUpstreamError,
)

# Retry decorator for rate-limited requests
_retry_on_rate_limit = retry(
    retry=retry_if_exception_type(ProviderRateLimitError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)


class BaseProviderClient(ABC):
    """Base class for all Zima provider clients.

    Providers fetch data from external APIs or local collectors.
    They return normalized raw data to modules.

    Providers MUST NOT:
      - assign severity or confidence scores
      - emit signals
      - know about tiers or which modules consume them
      - produce user-facing output or narratives
    """

    name: str

    def __init__(self, *, timeout_seconds: int = 15) -> None:
        self._timeout_seconds = timeout_seconds

    # ------------------------------------------------------------------
    # Async HTTP helpers (retry on 429 via tenacity)
    # ------------------------------------------------------------------

    @_retry_on_rate_limit
    async def _get(
        self,
        url: str,
        *,
        label: str = "",
        headers: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> Any:
        """GET request. Returns parsed JSON body, or {} for 404/empty."""
        timeout = timeout or self._timeout_seconds
        tag = label or self.name
        _timeout = httpx.Timeout(float(timeout), connect=min(5.0, float(timeout)))
        try:
            async with httpx.AsyncClient(
                timeout=_timeout, verify=True, follow_redirects=False
            ) as client:
                resp = await client.get(url, headers=headers or {})
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"{tag} request timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderTimeoutError(f"{tag} request failed") from exc
        self._check_status(resp, tag)
        if resp.status_code == 404:
            return {}
        return self._parse_json(resp, tag)

    @_retry_on_rate_limit
    async def _post(
        self,
        url: str,
        *,
        data: str | None = None,
        json_data: dict[str, Any] | None = None,
        label: str = "",
        headers: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> Any:
        """POST request. Returns parsed JSON body, or {} for 404/empty."""
        timeout = timeout or self._timeout_seconds
        tag = label or self.name
        _timeout = httpx.Timeout(float(timeout), connect=min(5.0, float(timeout)))
        try:
            async with httpx.AsyncClient(
                timeout=_timeout, verify=True, follow_redirects=False
            ) as client:
                resp = await client.post(
                    url,
                    content=data,
                    json=json_data,
                    headers=headers or {},
                )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(f"{tag} request timed out") from exc
        except httpx.HTTPError as exc:
            raise ProviderTimeoutError(f"{tag} request failed") from exc
        self._check_status(resp, tag)
        if resp.status_code == 404:
            return {}
        return self._parse_json(resp, tag)

    # ------------------------------------------------------------------
    # Response helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_status(resp: httpx.Response, label: str) -> None:
        """Raise typed errors for auth failures, rate limits, and server errors."""
        if resp.status_code in {401, 403}:
            raise ProviderAuthError(f"{label} rejected API key ({resp.status_code})")
        if resp.status_code == 429:
            raise ProviderRateLimitError(f"{label} rate limited")
        if resp.status_code >= 500:
            raise ProviderUpstreamError(
                f"{label} upstream error ({resp.status_code})",
                status_code=resp.status_code,
            )

    @staticmethod
    def _parse_json(resp: httpx.Response, label: str) -> Any:
        """Parse JSON from response. Returns {} for empty content."""
        if not resp.text.strip():
            return {}
        try:
            return resp.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise ProviderSchemaError(f"{label} JSON parse failed") from exc
