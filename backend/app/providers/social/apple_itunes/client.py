# backend/app/providers/social/apple_itunes/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_apple_itunes.py (MIT licensed)
# Copyright (c) bcoles.
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class AppleITunesProvider(BaseProviderClient):
    name = "apple_itunes"
    base_url = "https://itunes.apple.com/search"

    def __init__(self, timeout_seconds: int = 15, max_results: int = 100):
        self._timeout_seconds = timeout_seconds
        self._max_results = max_results

    async def search_itunes(
        self, *, domain: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        max_results = int(self._max_results)
        max_results = max(1, min(max_results, 200))

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if url is not None:
            _inputs.append(("url", url))
        for _entity_type, _value in _inputs:
            if _entity_type != "domain":
                continue
            domain = _value.strip().lower()
            if not domain:
                continue
            domain_reversed = ".".join(reversed(domain.split(".")))
            results = await self._query(domain_reversed, max_results)
            if not results:
                continue
            matched = 0
            for result in results:
                if not isinstance(result, dict):
                    continue
                bundle_id = str(result.get("bundleId", "")).strip().lower()
                track_name = str(result.get("trackName", "")).strip()
                version = str(result.get("version", "")).strip()
                track_url = str(result.get("trackViewUrl", "")).strip()
                if not bundle_id or not track_name or not version or not track_url:
                    continue
                if not self._bundle_matches(bundle_id, domain_reversed):
                    continue
                matched += 1
                findings.append(
                    dict(
                        provider=self.name,
                        category="attack_surface",
                        title="Apple App Store listing",
                        description=f"iTunes app '{track_name} {version}' matched bundle {bundle_id}",
                        entity_type="url",
                        entity_value=track_url,
                        confidence=0.7,
                        tags=["appstore", "mobile", "passive"],
                    )
                )
                seller_url = str(result.get("sellerUrl", "")).strip()
                if seller_url:
                    findings.append(
                        dict(
                            provider=self.name,
                            category="attack_surface",
                            title="App seller URL",
                            description=f"iTunes app seller URL discovered for bundle {bundle_id}",
                            entity_type="url",
                            entity_value=seller_url,
                            confidence=0.65,
                            tags=["appstore", "seller", "passive"],
                        )
                    )

            if matched > 0:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Apple iTunes query results for {domain}",
                        raw={
                            "domain": domain,
                            "matched_apps": matched,
                            "result_count": len(results),
                        },
                        confidence=0.7,
                    )
                )

        return findings

    async def _query(self, query: str, limit: int) -> list[dict]:
        params = urllib.parse.urlencode(
            {
                "media": "software",
                "entity": "software,iPadSoftware,softwareDeveloper",
                "limit": str(limit),
                "term": query,
            }
        )
        url = f"{self.base_url}?{params}"
        payload = await self._get(
            url, label="AppleITunes", timeout=self._timeout_seconds
        )
        if not isinstance(payload, dict):
            raise ProviderError(
                message="Apple iTunes schema changed: expected object payload",
                retryable=False,
            )
        results = payload.get("results", [])
        if not isinstance(results, list):
            raise ProviderError(
                message="Apple iTunes schema changed: expected results list",
                retryable=False,
            )
        return results

    @staticmethod
    def _bundle_matches(bundle_id: str, domain_reversed: str) -> bool:
        return (
            bundle_id == domain_reversed
            or bundle_id.startswith(f"{domain_reversed}.")
            or bundle_id.endswith(f".{domain_reversed}")
            or f".{domain_reversed}." in bundle_id
        )
