# backend/app/providers/threat_intel/h1nobbdde/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_h1nobbdde.py (MIT licensed)
import re
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class H1nobbddeProvider(BaseProviderClient):
    name = "h1nobbdde"
    base_url = "http://h1.nobbd.de/search.php"

    def __init__(self, timeout_seconds: int = 30):
        self._timeout_seconds = timeout_seconds

    async def check_defacement(self, domain: str) -> list[dict[str, Any]]:
        findings, evidence = [], []
        val = domain.strip()
        url = f"{self.base_url}?q={urllib.parse.quote(val)}"
        try:
            resp = await self._get(url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="h1.nobbd.de request failed", retryable=True
            ) from exc
        if resp.status_code != 200:
            raise ProviderError(
                message="h1.nobbd.de unexpected response", retryable=False
            )
        content = (
            resp.content
            if isinstance(resp.content, str)
            else resp.content.decode("utf-8", errors="replace")
        )
        reports = re.findall(r'href="(https?://hackerone\.com/reports/\d+)"', content)
        if reports:
            findings.append(
                dict(
                    provider=self.name,
                    category="vulnerability",
                    title=f"h1.nobbd.de: {val}",
                    description=f"{val} has {len(reports)} HackerOne vulnerability report(s) on h1.nobbd.de",
                    entity_type="domain",
                    entity_value=val,
                    confidence=0.80,
                    tags=["h1nobbdde", "vulnerability", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"h1.nobbd.de reports for {val}",
                    raw={"count": len(reports), "sample": reports[:3]},
                    confidence=0.80,
                )
            )
        return findings
