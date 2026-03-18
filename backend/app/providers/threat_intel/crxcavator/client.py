# backend/app/providers/threat_intel/crxcavator/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.LOW
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_crxcavator.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class CrxcavatorProvider(BaseProviderClient):
    name = "crxcavator"
    base_url = "https://api.crxcavator.io/v1"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def check_extensions(self, domain: str) -> list[dict[str, Any]]:
        findings, evidence = [], []
        seen: set[str] = set()
        val = domain.strip()
        url = f"{self.base_url}/search?{urllib.parse.urlencode({'q': val})}"
        data = self._fetch(url)
        results = data if isinstance(data, list) else []
        if not isinstance(results, list):
            return findings
        for item in results[:10]:
            if not isinstance(item, dict):
                continue
            ext_id = str(item.get("extension_id", "")).strip()
            name = str(item.get("name", "")).strip()
            if not ext_id or ext_id in seen:
                continue
            seen.add(ext_id)
            findings.append(
                dict(
                    provider=self.name,
                    category="software",
                    title=f"CRXcavator extension: {name or ext_id}",
                    description=f"Chrome extension referencing {val}: {name} ({ext_id})",
                    entity_type="domain",
                    entity_value=val,
                    confidence=0.65,
                    tags=["crxcavator", "chrome_extension", "passive"],
                )
            )
            if results:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"CRXcavator extensions for {val}",
                        raw={"count": len(results)},
                        confidence=0.65,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Crxcavator", timeout=self._timeout_seconds)
