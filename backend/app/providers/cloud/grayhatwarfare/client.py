# backend/app/providers/cloud/grayhatwarfare/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_grayhatwarfare.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class GrayhatwarfareProvider(BaseProviderClient):
    name = "grayhatwarfare"
    base_url = "https://buckets.grayhatwarfare.com/api/v1"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search_buckets(self, domain: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="GrayhatWarfare API key is required", retryable=False
            )
        headers = {"Authorization": f"Bearer {api_key}"}
        findings, evidence = [], []
        seen: set[str] = set()
        val = domain.strip()
        params = urllib.parse.urlencode({"keywords": val})
        url = f"{self.base_url}/buckets/0/100?{params}"
        data = self._fetch(url, headers)
        buckets = data.get("buckets", []) if isinstance(data, dict) else []
        if not isinstance(buckets, list):
            return findings
        for bucket in buckets[:20]:
            if not isinstance(bucket, dict):
                continue
            name = str(bucket.get("bucket", "") or bucket.get("name", "")).strip()
            provider_name = str(bucket.get("type", "")).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            findings.append(
                dict(
                    provider=self.name,
                    category="cloud_storage",
                    title=f"Cloud bucket: {name}",
                    description=f"Cloud storage bucket found for {val}: {name}"
                    + (f" ({provider_name})" if provider_name else ""),
                    entity_type="domain",
                    entity_value=val,
                    confidence=0.75,
                    tags=["grayhatwarfare", "cloud_storage", "passive"],
                )
            )
            if buckets:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"GrayhatWarfare buckets for {val}",
                        raw={"count": len(buckets)},
                        confidence=0.75,
                    )
                )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Grayhatwarfare", headers=headers, timeout=self._timeout_seconds
        )
