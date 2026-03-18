# backend/app/providers/social/debounce/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_debounce.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class DebounceProvider(BaseProviderClient):
    name = "debounce"
    base_url = "https://disposable.debounce.io"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def validate_email(
        self, *, domain: str | None = None, email: str | None = None
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"email", "domain"}:
                continue
            val = _value.strip()
            url = f"{self.base_url}?{urllib.parse.urlencode({'email': val})}"
            data = self._fetch(url)
            if not isinstance(data, dict):
                continue
            is_disposable = str(data.get("disposable", "0")).strip() == "1"
            if is_disposable:
                findings.append(
                    dict(
                        provider=self.name,
                        category="email_reputation",
                        title=f"Disposable email: {val}",
                        description=f"{val} is a disposable/temporary email address or domain",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.80,
                        tags=["debounce", "disposable", "email", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Debounce disposable check for {val}",
                        raw={"disposable": True},
                        confidence=0.80,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Debounce", timeout=self._timeout_seconds)
