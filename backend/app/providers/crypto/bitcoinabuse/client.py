# backend/app/providers/crypto/bitcoinabuse/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM if count < 5 else FindingSeverity.HIGH
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_bitcoinabuse.py (MIT licensed)
# Copyright (c) Steve Micallef.
import re
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class BitcoinAbuseProvider(BaseProviderClient):
    name = "bitcoinabuse"
    base_url = "https://www.bitcoinabuse.com/api/reports/check"
    _btc_re = re.compile(
        r"^(?:[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[ac-hj-np-z02-9]{11,71})$"
    )

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def check_abuse(self, address: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="BitcoinAbuse API key is required",
                retryable=False,
            )

        findings = []
        evidence = []
        address = address.strip()
        if not address:
            return findings
        if not self._is_valid_btc_address(address):
            raise ProviderError(
                message=f"Unsupported input for BitcoinAbuse query: {address}",
                retryable=False,
            )

        payload = await self._query_address(address, api_key)
        count = payload.get("count")
        if count is None:
            raise ProviderError(
                message="BitcoinAbuse schema changed: missing count field",
                retryable=False,
            )
        if not isinstance(count, int):
            raise ProviderError(
                message="BitcoinAbuse schema changed: invalid count field type",
                retryable=False,
            )
        if count <= 0:
            return findings

        findings.append(
            dict(
                provider=self.name,
                category="reputation",
                title="Bitcoin address reported by BitcoinAbuse",
                description=f"{address} has {count} reports in BitcoinAbuse",
                entity_type="bitcoin_address",
                entity_value=address,
                confidence=0.8,
                tags=["crypto", "bitcoin", "reputation", "passive"],
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description=f"BitcoinAbuse check response for {address}",
                raw=payload,
                confidence=0.8,
            )
        )

        return findings

    async def _query_address(self, address: str, api_key: str) -> dict:
        query = urllib.parse.urlencode({"address": address, "api_token": api_key})
        url = f"{self.base_url}?{query}"
        payload = await self._get(
            url, label="BitcoinAbuse", timeout=self._timeout_seconds
        )
        if not isinstance(payload, dict):
            raise ProviderError(
                message="BitcoinAbuse schema changed: expected object payload",
                retryable=False,
            )
        return payload

    @classmethod
    def _is_valid_btc_address(cls, value: str) -> bool:
        return bool(cls._btc_re.match(value))
