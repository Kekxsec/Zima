# backend/app/providers/breach/pastebin/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_pastebin.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class PastebinProvider(BaseProviderClient):
    name = "pastebin"
    # Uses Google CSE or psbdmp, or direct scraping
    base_url = "https://psbdmp.ws/api/v3/search"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def search_pastes(
        self, *, domain: str | None = None, email: str | None = None
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "email"}:
                continue
            val = _value.strip()
            url = f"{self.base_url}/{urllib.parse.quote(val)}"
            data = self._fetch(url)
            pastes = data.get("data", []) if isinstance(data, dict) else []
            if not isinstance(pastes, list):
                continue
            for paste in pastes[:10]:
                if not isinstance(paste, dict):
                    continue
                paste_id = str(paste.get("id", "")).strip()
                if not paste_id or paste_id in seen:
                    continue
                seen.add(paste_id)
                findings.append(
                    dict(
                        provider=self.name,
                        category="data_leak",
                        title=f"Pastebin: {val}",
                        description=f"{val} found in pastebin paste ID: {paste_id}",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.72,
                        tags=["pastebin", "leak", "passive"],
                    )
                )
            if pastes:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Pastebin pastes for {val}",
                        raw={"count": len(pastes)},
                        confidence=0.72,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Pastebin", timeout=self._timeout_seconds)
