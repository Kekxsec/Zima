# backend/app/providers/crypto/etherscan/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_etherscan.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class EtherscanProvider(BaseProviderClient):
    name = "etherscan"
    base_url = "https://api.etherscan.io/api"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_token_info(self, address: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="Etherscan API key is required", retryable=False
            )
        findings, evidence = [], []
        val = address.strip()
        url = f"{self.base_url}?module=account&action=balance&address={urllib.parse.quote(val)}&tag=latest&apikey={api_key}"
        data = self._fetch(url)
        if not isinstance(data, dict):
            return findings
        if data.get("status") != "1":
            return findings
        balance_wei = str(data.get("result", "0")).strip()
        try:
            balance_eth = int(balance_wei) / 1e18
        except (ValueError, TypeError):
            balance_eth = 0.0
        if balance_eth > 0:
            findings.append(
                dict(
                    provider=self.name,
                    category="cryptocurrency",
                    title=f"Etherscan balance: {val[:12]}...",
                    description=f"Ethereum address {val} has balance: {balance_eth:.6f} ETH",
                    entity_type="ethereum_address",
                    entity_value=val,
                    confidence=0.95,
                    tags=["etherscan", "ethereum", "crypto", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"Etherscan balance for {val}",
                    raw={"balance_eth": balance_eth, "balance_wei": balance_wei},
                    confidence=0.95,
                )
            )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Etherscan", timeout=self._timeout_seconds)
