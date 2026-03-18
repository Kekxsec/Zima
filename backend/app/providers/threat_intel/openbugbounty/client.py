# backend/app/providers/threat_intel/openbugbounty/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_openbugbounty.py (MIT licensed)
import re
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class OpenbugbountyProvider(BaseProviderClient):
    name = "openbugbounty"
    base_url = "https://www.openbugbounty.org/api/1/search"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def check_defacement(self, domain: str) -> list[dict[str, Any]]:
        findings, evidence = [], []
        val = domain.strip()
        url = f"{self.base_url}/?{urllib.parse.urlencode({'domain': val})}"
        try:
            resp = await self._get(url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="OpenBugBounty request failed", retryable=True
            ) from exc
        if resp.status_code == 429:
            raise ProviderError(message="OpenBugBounty rate limited", retryable=True)
        if resp.status_code != 200:
            raise ProviderError(
                message="OpenBugBounty unexpected response", retryable=False
            )
        content = (
            resp.content
            if isinstance(resp.content, str)
            else resp.content.decode("utf-8", errors="replace")
        )
        # Parse XML response
        reports = re.findall(
            r"<url>(https://www\.openbugbounty\.org/reports/\d+/)</url>", content
        )
        if reports:
            findings.append(
                dict(
                    provider=self.name,
                    category="vulnerability",
                    title=f"OpenBugBounty: {val}",
                    description=f"{val} has {len(reports)} vulnerability report(s) on OpenBugBounty",
                    entity_type="domain",
                    entity_value=val,
                    confidence=0.82,
                    tags=["openbugbounty", "vulnerability", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"OpenBugBounty reports for {val}",
                    raw={"count": len(reports), "sample": reports[:3]},
                    confidence=0.82,
                )
            )
        return findings
