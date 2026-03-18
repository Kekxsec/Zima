# backend/app/providers/social/googlemaps/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_googlemaps.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class GooglemapsProvider(BaseProviderClient):
    name = "googlemaps"
    base_url = "https://maps.googleapis.com/maps/api/geocode/json"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search_maps(self, address: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="Google Maps API key is required", retryable=False
            )
        findings, evidence = [], []
        val = address.strip()
        url = f"{self.base_url}?{urllib.parse.urlencode({'key': api_key, 'address': val})}"
        data = self._fetch(url)
        if not isinstance(data, dict):
            return findings
        status = data.get("status", "")
        results = data.get("results", [])
        if status == "OK" and results:
            loc = results[0].get("formatted_address", val)
            lat_lng = results[0].get("geometry", {}).get("location", {})
            findings.append(
                dict(
                    provider=self.name,
                    category="geo_info",
                    title=f"Google Maps: {val[:50]}",
                    description=f"Geocoded location: {loc}"
                    + (
                        f" ({lat_lng.get('lat')},{lat_lng.get('lng')})"
                        if lat_lng
                        else ""
                    ),
                    entity_type="physical_address",
                    entity_value=val,
                    confidence=0.80,
                    tags=["googlemaps", "geo", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"Google Maps geocode for {val}",
                    raw={"formatted_address": loc, "latlng": lat_lng},
                    confidence=0.80,
                )
            )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Googlemaps", timeout=self._timeout_seconds)
