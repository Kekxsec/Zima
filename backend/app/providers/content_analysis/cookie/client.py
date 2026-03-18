# backend/app/providers/content_analysis/cookie/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_cookie.py (MIT licensed)
# Copyright (c) Steve Micallef.
import json
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class CookieProvider(BaseProviderClient):
    name = "cookie"

    async def check_cookies(self, content: str) -> list[dict[str, Any]]:
        include_values = False
        findings = []
        evidence = []
        seen = set()
        headers = self._parse_headers(content)
        if not headers:
            return findings
        cookie_value = str(
            headers.get("cookie") or headers.get("set-cookie") or ""
        ).strip()
        if not cookie_value:
            return findings
        parsed_value = (
            cookie_value if include_values else self._sanitize_cookie(cookie_value)
        )
        if not parsed_value or parsed_value in seen:
            return findings
        seen.add(parsed_value)
        findings.append(
            dict(
                provider=self.name,
                category="identity_exposure",
                title="Cookie header extracted",
                description="HTTP cookie data was extracted from supplied header content",
                entity_type="web_content",
                entity_value=parsed_value,
                confidence=0.61,
                tags=["content_analysis", "cookie", "passive"],
            )
        )
        evidence.append(
            dict(
                source=self.name,
                description="Cookie extracted from HTTP header payload",
                raw={
                    "cookie_name_count": len(
                        [item for item in parsed_value.split(";") if item.strip()]
                    )
                },
                confidence=0.61,
            )
        )
        return findings

    @staticmethod
    def _parse_headers(raw: str) -> dict:
        if not raw or not raw.strip():
            return {}
        try:
            payload = json.loads(raw)
        except Exception as exc:
            raise ProviderError(
                message="Cookie provider expected JSON-encoded HTTP headers",
                retryable=False,
            ) from exc
        if not isinstance(payload, dict):
            raise ProviderError(
                message="Cookie provider schema changed: expected JSON object",
                retryable=False,
            )
        return {str(k).strip().lower(): str(v) for k, v in payload.items()}

    @staticmethod
    def _sanitize_cookie(cookie_header: str) -> str:
        names = []
        for token in cookie_header.split(";"):
            part = token.strip()
            if not part or "=" not in part:
                continue
            name = part.split("=", 1)[0].strip()
            if not name:
                continue
            names.append(name)
        return "; ".join(dict.fromkeys(names))
