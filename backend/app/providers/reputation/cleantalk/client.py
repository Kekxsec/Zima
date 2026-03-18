# backend/app/providers/reputation/cleantalk/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---

# Adapted from SpiderFoot module: modules/sfp_cleantalk.py (MIT licensed)

BLOCKLIST_URL = "https://iplists.firehol.org/files/cleantalk_7d.ipset"


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class CleantalkProvider(BaseProviderClient):
    name = "cleantalk"

    def __init__(self, timeout_seconds: int = 30):
        self._timeout_seconds = timeout_seconds

    async def get_reputation(self, ip_address: str) -> list[dict[str, Any]]:
        findings, evidence = [], []
        try:
            resp = await self._get(BLOCKLIST_URL, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="CleanTalk list fetch failed", retryable=True
            ) from exc
        if resp.status_code != 200:
            raise ProviderError(
                message="CleanTalk list unexpected response", retryable=False
            )
        content = (
            resp.content
            if isinstance(resp.content, str)
            else resp.content.decode("utf-8", errors="replace")
        )
        blocked_ips = {
            line.strip()
            for line in content.splitlines()
            if line.strip() and not line.startswith("#")
        }

        val = ip_address.strip()
        if val in blocked_ips:
            findings.append(
                dict(
                    provider=self.name,
                    category="blocklist",
                    title=f"CleanTalk blocklist: {val}",
                    description=f"IP {val} is in CleanTalk spam blocklist (7-day)",
                    entity_type="ip_address",
                    entity_value=val,
                    confidence=0.75,
                    tags=["cleantalk", "spam", "blocklist", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"CleanTalk blocklist match for {val}",
                    raw={"blocked": True},
                    confidence=0.75,
                )
            )
        return findings
