# backend/app/providers/darkweb/torch/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_torch.py (MIT licensed)
import re
import urllib.parse
from typing import Any

ONION_RE = re.compile(r"https?://([a-z2-7]{16,56}\.onion)", re.IGNORECASE)


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class TorchProvider(BaseProviderClient):
    name = "torch"
    base_url = "https://torch.onl/search"

    def __init__(self, timeout_seconds: int = 30):
        self._timeout_seconds = timeout_seconds

    async def search_darkweb(
        self,
        *,
        domain: str | None = None,
        email: str | None = None,
        name: str | None = None,
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        if name is not None:
            _inputs.append(("name", name))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "email", "human_name"}:
                continue
            val = _value.strip()
            params = urllib.parse.urlencode({"q": val})
            url = f"{self.base_url}?{params}"
            try:
                resp = await self._get(url, timeout=self._timeout_seconds)
            except Exception as exc:
                raise ProviderError(
                    message="Torch request failed", retryable=True
                ) from exc
            if resp.status_code == 429:
                raise ProviderError(message="Torch rate limited", retryable=True)
            if resp.status_code != 200:
                continue
            content = (
                resp.content
                if isinstance(resp.content, str)
                else resp.content.decode("utf-8", errors="replace")
            )
            onion_urls = list(dict.fromkeys(ONION_RE.findall(content)))
            for onion in onion_urls[:10]:
                if onion in seen:
                    continue
                seen.add(onion)
                findings.append(
                    dict(
                        provider=self.name,
                        category="dark_web",
                        title=f"Torch .onion: {onion}",
                        description=f"Torch dark web search for {val} found .onion site: {onion}",
                        entity_type="domain",
                        entity_value=onion,
                        confidence=0.65,
                        tags=["torch", "dark_web", "onion", "passive"],
                    )
                )
            if onion_urls:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Torch search results for {val}",
                        raw={"onion_count": len(onion_urls), "sample": onion_urls[:5]},
                        confidence=0.65,
                    )
                )
        return findings
