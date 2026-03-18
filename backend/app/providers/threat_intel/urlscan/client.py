# backend/app/providers/threat_intel/urlscan/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity = FindingSeverity.HIGH if malicious else FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_urlscan.py (MIT licensed)
# Copyright (c) Steve Micallef.
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class UrlscanProvider(BaseProviderClient):
    name = "urlscan"
    base_url = "https://urlscan.io/api/v1/search/"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search_scans(
        self,
        *,
        domain: str | None = None,
        ip_address: str | None = None,
        url: str | None = None,
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        headers = {"API-Key": api_key} if api_key else {}

        findings = []
        evidence = []
        seen: set[str] = set()

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        if url is not None:
            _inputs.append(("url", url))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "ip_address", "url"}:
                continue
            value = _value.strip()
            if _entity_type == "domain":
                q = f"domain:{value}"
            elif _entity_type == "ip_address":
                q = f"ip:{value}"
            else:
                q = f"page.url:{value}"

            params = urllib.parse.urlencode({"q": q, "size": "100"})
            url = f"{self.base_url}?{params}"
            data = await self._get(
                url, label="URLScan", headers=headers, timeout=self._timeout_seconds
            )
            results = data.get("results", [])
            if not isinstance(results, list):
                continue
            for item in results:
                if not isinstance(item, dict):
                    continue
                page = item.get("page", {})
                if not isinstance(page, dict):
                    continue
                scan_url = str(page.get("url", "")).strip()
                malicious = (
                    item.get("verdicts", {}).get("overall", {}).get("malicious", False)
                )
                if not scan_url or scan_url in seen:
                    continue
                seen.add(scan_url)

                findings.append(
                    dict(
                        provider=self.name,
                        category="url_scan",
                        title=f"URLScan result: {scan_url[:80]}",
                        description=f"URLScan found scan for {value}: {scan_url}"
                        + (" [MALICIOUS]" if malicious else ""),
                        entity_type="url",
                        entity_value=scan_url,
                        confidence=0.72,
                        tags=["urlscan", "passive", "malicious"]
                        if malicious
                        else ["urlscan", "passive"],
                    )
                )
            if results:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"URLScan results for {value}",
                        raw={"count": len(results)},
                        confidence=0.72,
                    )
                )

        return findings
