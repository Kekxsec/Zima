# backend/app/providers/threat_intel/cybercrimetracker/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---

# Adapted from SpiderFoot module: modules/sfp_cybercrimetracker.py (MIT licensed)

FEED_URL = "https://cybercrime-tracker.net/all.php"


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class CybercrimetrackerProvider(BaseProviderClient):
    name = "cybercrimetracker"

    def __init__(self, timeout_seconds: int = 30):
        self._timeout_seconds = timeout_seconds

    async def check_crimeware(
        self,
        *,
        domain: str | None = None,
        ip_address: str | None = None,
        url: str | None = None,
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        try:
            resp = await self._get(FEED_URL, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="CyberCrime Tracker fetch failed", retryable=True
            ) from exc
        if resp.status_code != 200:
            raise ProviderError(
                message="CyberCrime Tracker unexpected response", retryable=False
            )
        content = (
            resp.content
            if isinstance(resp.content, str)
            else resp.content.decode("utf-8", errors="replace")
        )
        entries = {
            line.strip().lower()
            for line in content.splitlines()
            if line.strip() and not line.startswith("#")
        }

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
            val = _value.strip()
            check = val.lower()
            matched = any(check in entry or entry in check for entry in entries)
            if matched:
                findings.append(
                    dict(
                        provider=self.name,
                        category="malware",
                        title=f"CyberCrime Tracker: {val}",
                        description=f"{val} found in CyberCrime Tracker malware feed",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.80,
                        tags=["cybercrimetracker", "malware", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"CyberCrime Tracker match for {val}",
                        raw={"matched": True},
                        confidence=0.80,
                    )
                )
        return findings
