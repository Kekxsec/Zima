# backend/app/providers/domain/whoxy/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_whoxy.py (MIT licensed)
# Copyright (c) Steve Micallef.
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class WhoxyProvider(BaseProviderClient):
    name = "whoxy"
    base_url = "https://api.whoxy.com/"

    def __init__(
        self, api_key: str = "", timeout_seconds: int = 15, max_pages: int = 10
    ):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._max_pages = max_pages

    async def lookup_whois(
        self, *, domain: str | None = None, email: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="Whoxy API key is required",
                retryable=False,
            )

        try:
            max_pages = int(self._max_pages)
        except (TypeError, ValueError) as exc:
            raise ProviderError(
                message="Invalid whoxy option: max_pages must be an integer",
                retryable=False,
            ) from exc
        max_pages = max(1, min(max_pages, 50))
        findings = []
        evidence = []

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        for _entity_type, _value in _inputs:
            if _entity_type != "email":
                continue
            email = _value.strip().lower()
            if not email:
                continue

            seen_domains = set()
            total_records = 0
            for page in range(1, max_pages + 1):
                payload = await self._query_whoxy(api_key, email, page)
                if not payload:
                    break

                status = int(payload.get("status", 0))
                if status == 0:
                    status_reason = str(payload.get("status_reason", "Unknown"))
                    raise ProviderError(
                        message=f"Whoxy query failed: {status_reason}",
                        retryable=False,
                    )

                records = payload.get("search_result", [])
                if not isinstance(records, list):
                    raise ProviderError(
                        message="Whoxy schema changed: expected search_result list",
                        retryable=False,
                    )
                total_records += len(records)
                for rec in records:
                    if not isinstance(rec, dict):
                        continue
                    domain = str(rec.get("domain_name", "")).strip().lower()
                    if not domain or domain in seen_domains:
                        continue
                    seen_domains.add(domain)
                    findings.append(
                        dict(
                            provider=self.name,
                            category="account_exposure",
                            title="Reverse WHOIS domain",
                            description=f"Whoxy reverse WHOIS found domain {domain} for {email}",
                            entity_type="domain",
                            entity_value=domain,
                            confidence=0.7,
                            tags=["reverse_whois", "passive"],
                        )
                    )

                current_page = int(payload.get("current_page", page))
                total_pages = int(payload.get("total_pages", page))
                if current_page >= total_pages:
                    break

            if total_records > 0:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Whoxy reverse WHOIS lookup for {email}",
                        raw={"email": email, "record_count": total_records},
                        confidence=0.7,
                    )
                )

        return findings

    async def _query_whoxy(self, api_key: str, email: str, page: int) -> dict:
        params = urllib.parse.urlencode(
            {
                "key": api_key,
                "reverse": "whois",
                "email": email,
                "page": str(page),
            }
        )
        url = f"{self.base_url}?{params}"
        payload = await self._get(url, label="Whoxy", timeout=self._timeout_seconds)
        if not isinstance(payload, dict):
            raise ProviderError(
                message="Whoxy schema changed: expected object payload",
                retryable=False,
            )
        return payload
