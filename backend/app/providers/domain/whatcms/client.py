# backend/app/providers/domain/whatcms/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_whatcms.py (MIT licensed)
# Copyright (c) Steve Micallef.
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class WhatcmsProvider(BaseProviderClient):
    name = "whatcms"
    base_url = "https://whatcms.org/API/Tech"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_tech_stack(
        self, *, domain: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(message="WhatCMS API key is required", retryable=False)

        findings = []
        evidence = []
        seen: set[str] = set()

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if url is not None:
            _inputs.append(("url", url))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "url"}:
                continue
            target = _value.strip()
            if _entity_type == "domain":
                target = f"https://{target}"
            params = urllib.parse.urlencode({"key": api_key, "url": target})
            url = f"{self.base_url}?{params}"
            data = await self._get(url, label="WhatCMS", timeout=self._timeout_seconds)
            if not isinstance(data, dict):
                raise ProviderError(
                    message="WhatCMS schema changed",
                    retryable=False,
                )
            result = data.get("result", {})
            if not isinstance(result, dict):
                continue
            cms_name = str(result.get("name", "")).strip()
            if not cms_name or cms_name in seen:
                continue
            seen.add(cms_name)
            findings.append(
                dict(
                    provider=self.name,
                    category="technology_fingerprint",
                    title=f"CMS detected: {cms_name}",
                    description=f"{target} is running {cms_name}",
                    entity_type="domain",
                    entity_value=_value,
                    confidence=0.80,
                    tags=["whatcms", "cms", "fingerprint", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"WhatCMS detection for {target}",
                    raw={"cms": cms_name, "version": result.get("version", "")},
                    confidence=0.80,
                )
            )

        return findings
