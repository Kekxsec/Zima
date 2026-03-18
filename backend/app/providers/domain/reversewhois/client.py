# backend/app/providers/domain/reversewhois/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_reversewhois.py (MIT licensed)
import re
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ReversewhoisProvider(BaseProviderClient):
    name = "reversewhois"
    base_url = "https://reversewhois.io"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def lookup_whois(
        self, *, email: str | None = None, name: str | None = None
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if email is not None:
            _inputs.append(("email", email))
        if name is not None:
            _inputs.append(("name", name))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"email", "human_name"}:
                continue
            val = _value.strip()
            url = f"{self.base_url}?searchterm={urllib.parse.quote(val)}"
            try:
                resp = await self._get(url, timeout=self._timeout_seconds)
            except Exception as exc:
                raise ProviderError(
                    message="ReverseWhois request failed", retryable=True
                ) from exc
            if resp.status_code == 429:
                raise ProviderError(message="ReverseWhois rate limited", retryable=True)
            if resp.status_code != 200:
                raise ProviderError(
                    message="ReverseWhois unexpected response", retryable=False
                )
            content = (
                resp.content
                if isinstance(resp.content, str)
                else resp.content.decode("utf-8", errors="replace")
            )
            # Extract domain counts from HTML
            domains = re.findall(
                r"([a-zA-Z0-9][a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,})", content
            )
            unique_domains = list(
                dict.fromkeys(
                    d for d in domains if len(d) > 4 and "reversewhois" not in d
                )
            )[:20]
            if unique_domains:
                findings.append(
                    dict(
                        provider=self.name,
                        category="whois",
                        title=f"ReverseWhois: {val}",
                        description=f"Reverse WHOIS found {len(unique_domains)} domain(s) registered to {val}",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.65,
                        tags=["reversewhois", "whois", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"ReverseWhois for {val}",
                        raw={"domains": unique_domains[:10]},
                        confidence=0.65,
                    )
                )
        return findings
