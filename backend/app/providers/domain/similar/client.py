# backend/app/providers/domain/similar/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_similar.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class SimilarProvider(BaseProviderClient):
    name = "similar"
    base_url = "https://api.similarweb.com/v1/similar-rank"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def find_similar(self, domain: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="SimilarWeb API key is required", retryable=False
            )
        findings, evidence = [], []
        val = domain.strip()
        url = f"{self.base_url}/{urllib.parse.quote(val)}/rank?api_key={api_key}"
        data = self._fetch(url)
        if not isinstance(data, dict):
            return findings
        rank = (
            data.get("SimilarRank", {}).get("Rank")
            if isinstance(data.get("SimilarRank"), dict)
            else None
        )
        if rank:
            findings.append(
                dict(
                    provider=self.name,
                    category="web_analytics",
                    title=f"SimilarWeb: {val}",
                    description=f"SimilarWeb rank for {val}: #{rank}",
                    entity_type="domain",
                    entity_value=val,
                    confidence=0.72,
                    tags=["similar", "web_analytics", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"SimilarWeb rank for {val}",
                    raw={"rank": rank},
                    confidence=0.72,
                )
            )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Similar", timeout=self._timeout_seconds)
