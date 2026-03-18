# backend/app/providers/reputation/adblock/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.LOW
# --- End migration notes ---

# Adapted from SpiderFoot module: modules/sfp_adblock.py (MIT licensed)

BLOCKLIST_URL = "https://easylist.to/easylist/easylist.txt"


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class AdblockProvider(BaseProviderClient):
    name = "adblock"

    def __init__(self, timeout_seconds: int = 30):
        self._timeout_seconds = timeout_seconds

    async def get_reputation(
        self, *, domain: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        try:
            resp = await self._get(BLOCKLIST_URL, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="EasyList fetch failed", retryable=True
            ) from exc
        if resp.status_code != 200:
            raise ProviderError(message="EasyList unexpected response", retryable=False)
        content = (
            resp.content
            if isinstance(resp.content, str)
            else resp.content.decode("utf-8", errors="replace")
        )
        rules = [
            line.strip()
            for line in content.splitlines()
            if line.strip() and not line.startswith("!")
        ]

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if url is not None:
            _inputs.append(("url", url))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"url", "domain"}:
                continue
            val = _value.strip()
            matched = any(rule in val for rule in rules[:1000] if len(rule) > 5)
            if matched:
                findings.append(
                    dict(
                        provider=self.name,
                        category="blocked_content",
                        title=f"Adblock blocked: {val}",
                        description=f"URL/domain {val} matches EasyList adblock rules",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.70,
                        tags=["adblock", "tracking", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"EasyList match for {val}",
                        raw={"blocked": True},
                        confidence=0.70,
                    )
                )
        return findings
