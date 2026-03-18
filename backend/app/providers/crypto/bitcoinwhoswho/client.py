# backend/app/providers/crypto/bitcoinwhoswho/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_bitcoinwhoswho.py (MIT licensed)
# Copyright (c) Steve Micallef.
import re
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class BitcoinWhosWhoProvider(BaseProviderClient):
    name = "bitcoinwhoswho"
    base_url = "https://bitcoinwhoswho.com/api/scam"
    _btc_re = re.compile(
        r"^(?:[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[ac-hj-np-z02-9]{11,71})$"
    )

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_address_info(self, address: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="BitcoinWhosWho API key is required",
                retryable=False,
            )

        findings = []
        evidence = []
        address = address.strip()
        if not address:
            return findings
        if not self._is_valid_btc_address(address):
            raise ProviderError(
                message=f"Unsupported input for BitcoinWhosWho query: {address}",
                retryable=False,
            )

        payload = await self._query_address(address, api_key)
        scams = payload.get("scams", [])
        if not isinstance(scams, list):
            raise ProviderError(
                message="BitcoinWhosWho schema changed: expected scams list",
                retryable=False,
            )
        if not scams:
            return findings

        findings.append(
            dict(
                provider=self.name,
                category="reputation",
                title="Bitcoin address reported by BitcoinWhosWho",
                description=f"{address} appears in BitcoinWhosWho scam dataset",
                entity_type="bitcoin_address",
                entity_value=address,
                confidence=0.75,
                tags=["crypto", "bitcoin", "reputation", "passive"],
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description=f"BitcoinWhosWho scam response for {address}",
                raw=payload,
                confidence=0.75,
            )
        )

        return findings

    async def _query_address(self, address: str, api_key: str) -> dict:
        query = urllib.parse.urlencode({"address": address})
        url = f"{self.base_url}/{urllib.parse.quote(api_key)}?{query}"
        payload = await self._get(
            url, label="BitcoinWhosWho", timeout=self._timeout_seconds
        )
        if not isinstance(payload, dict):
            raise ProviderError(
                message="BitcoinWhosWho schema changed: expected object payload",
                retryable=False,
            )
        return payload

    @classmethod
    def _is_valid_btc_address(cls, value: str) -> bool:
        return bool(cls._btc_re.match(value))
