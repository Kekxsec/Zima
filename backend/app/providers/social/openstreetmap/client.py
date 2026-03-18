# backend/app/providers/social/openstreetmap/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_openstreetmap.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class OpenstreetmapProvider(BaseProviderClient):
    name = "openstreetmap"
    base_url = "https://nominatim.openstreetmap.org/search"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def search_maps(self, address: str) -> list[dict[str, Any]]:
        findings, evidence = [], []
        val = address.strip()
        params = urllib.parse.urlencode(
            {"q": val, "format": "json", "addressdetails": "1", "limit": "5"}
        )
        url = f"{self.base_url}?{params}"
        data = self._fetch(url)
        results = data if isinstance(data, list) else []
        for item in results[:5]:
            if not isinstance(item, dict):
                continue
            display_name = str(item.get("display_name", "")).strip()
            lat = item.get("lat")
            lon = item.get("lon")
            if display_name:
                findings.append(
                    dict(
                        provider=self.name,
                        category="geo_info",
                        title=f"OSM: {val[:50]}",
                        description=f"OpenStreetMap geocode: {display_name}"
                        + (f" ({lat},{lon})" if lat and lon else ""),
                        entity_type="physical_address",
                        entity_value=val,
                        confidence=0.75,
                        tags=["openstreetmap", "geo", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"OSM geocode for {val}",
                        raw={"display_name": display_name, "lat": lat, "lon": lon},
                        confidence=0.75,
                    )
                )
                break
        return findings

    async def _fetch(self, url: str) -> list:
        return await self._get(
            url, label="Openstreetmap", timeout=self._timeout_seconds
        )
