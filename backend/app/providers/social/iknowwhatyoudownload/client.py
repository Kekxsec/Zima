# backend/app/providers/social/iknowwhatyoudownload/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_iknowwhatyoudownload.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class IknowwhatyoudownloadProvider(BaseProviderClient):
    name = "iknowwhatyoudownload"
    base_url = "https://iknowwhatyoudownload.com/api/peer"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_downloads(self, ip_address: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        findings, evidence = [], []
        val = ip_address.strip()
        params: dict = {"ip": val}
        if api_key:
            params["key"] = api_key
        url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
        data = self._fetch(url)
        if not isinstance(data, dict):
            return findings
        contents = data.get("contents", []) or []
        if not isinstance(contents, list):
            return findings
        if contents:
            torrents = [
                str(c.get("name", "") or c.get("torrent", {}).get("name", ""))
                for c in contents[:5]
                if isinstance(c, dict)
            ]
            findings.append(
                dict(
                    provider=self.name,
                    category="torrent_activity",
                    title=f"iKWYD: {val}",
                    description=f"IP {val} has {len(contents)} torrent download record(s) via iknowwhatyoudownload.com",
                    entity_type="ip_address",
                    entity_value=val,
                    confidence=0.75,
                    tags=["iknowwhatyoudownload", "torrent", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"iKWYD data for {val}",
                    raw={
                        "count": len(contents),
                        "sample": [t for t in torrents if t][:3],
                    },
                    confidence=0.75,
                )
            )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(
            url, label="Iknowwhatyoudownload", timeout=self._timeout_seconds
        )
