# backend/app/providers/crypto/blockchain/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_blockchain.py (MIT licensed)
# Copyright (c) Steve Micallef.
import re
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class BlockchainProvider(BaseProviderClient):
    name = "blockchain"
    base_url = "https://blockchain.info/balance"
    _btc_re = re.compile(
        r"^(?:[13][a-km-zA-HJ-NP-Z1-9]{25,34}|bc1[ac-hj-np-z02-9]{11,71})$"
    )

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def get_transactions(self, address: str) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        address = address.strip()
        if not address:
            return findings
        if not self._is_valid_btc_address(address):
            raise ProviderError(
                message=f"Unsupported input for blockchain balance query: {address}",
                retryable=False,
            )

        payload = await self._query_balance(address)
        entry = payload.get(address)
        if not isinstance(entry, dict):
            raise ProviderError(
                message="Blockchain schema changed: missing address object",
                retryable=False,
            )
        final_balance = entry.get("final_balance")
        if not isinstance(final_balance, int):
            raise ProviderError(
                message="Blockchain schema changed: missing final_balance",
                retryable=False,
            )
        balance_btc = final_balance / 100000000.0

        findings.append(
            dict(
                provider=self.name,
                category="infrastructure_intel",
                title="Bitcoin wallet balance observed",
                description=f"Blockchain reports current final balance {balance_btc:.8f} BTC for {address}",
                entity_type="bitcoin_address",
                entity_value=address,
                confidence=0.8,
                tags=["crypto", "bitcoin", "passive"],
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description=f"Blockchain balance response for {address}",
                raw={
                    "address": address,
                    "final_balance_satoshi": final_balance,
                    "final_balance_btc": balance_btc,
                },
                confidence=0.8,
            )
        )

        return findings

    async def _query_balance(self, address: str) -> dict:
        params = urllib.parse.urlencode({"active": address})
        url = f"{self.base_url}?{params}"
        payload = await self._get(
            url, label="Blockchain", timeout=self._timeout_seconds
        )
        if not isinstance(payload, dict):
            raise ProviderError(
                message="Blockchain schema changed: expected object payload",
                retryable=False,
            )
        return payload

    @classmethod
    def _is_valid_btc_address(cls, value: str) -> bool:
        return bool(cls._btc_re.match(value))
