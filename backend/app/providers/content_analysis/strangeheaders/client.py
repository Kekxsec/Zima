# backend/app/providers/content_analysis/strangeheaders/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.LOW
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_strangeheaders.py (MIT licensed)
# Copyright (c) Steve Micallef.
import json
from typing import Any

_STANDARD_HEADERS = frozenset(
    [
        "accept-ranges",
        "age",
        "allow",
        "cache-control",
        "connection",
        "content-encoding",
        "content-language",
        "content-length",
        "content-location",
        "content-md5",
        "content-range",
        "content-type",
        "date",
        "etag",
        "expires",
        "last-modified",
        "link",
        "location",
        "p3p",
        "pragma",
        "proxy-authenticate",
        "refresh",
        "retry-after",
        "server",
        "set-cookie",
        "strict-transport-security",
        "trailer",
        "transfer-encoding",
        "upgrade",
        "vary",
        "via",
        "warning",
        "www-authenticate",
        "x-content-type-options",
        "x-frame-options",
        "x-xss-protection",
        "x-powered-by",
        "access-control-allow-origin",
        "access-control-allow-methods",
        "access-control-allow-headers",
        "access-control-max-age",
        "x-request-id",
        "x-correlation-id",
        "x-cache",
        "x-forwarded-for",
        "x-real-ip",
        "cf-ray",
        "cf-cache-status",
        "alt-svc",
        "nel",
        "report-to",
        "permissions-policy",
        "feature-policy",
        "content-security-policy",
        "referrer-policy",
        "expect-ct",
    ]
)


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class StrangeheadersProvider(BaseProviderClient):
    """Detect non-standard or suspicious HTTP response headers."""

    name = "strangeheaders"

    async def check_headers(self, content: str) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen: set[str] = set()

        if not content:
            return findings
        try:
            headers = json.loads(content)
        except Exception as exc:
            raise ProviderError(
                message="strangeheaders provider expected JSON-encoded HTTP headers",
                retryable=False,
            ) from exc
        if not isinstance(headers, dict):
            return findings
        for header_name in headers:
            name_lower = str(header_name).lower().strip()
            if name_lower in _STANDARD_HEADERS:
                continue
            if name_lower in seen:
                continue
            seen.add(name_lower)
            findings.append(
                dict(
                    provider=self.name,
                    category="information_disclosure",
                    title=f"Non-standard HTTP header: {header_name}",
                    description=f"Unusual HTTP response header detected: {header_name}",
                    entity_type="web_content",
                    entity_value=str(header_name),
                    confidence=0.60,
                    tags=["content_analysis", "strangeheaders", "passive"],
                )
            )
        if findings:
            evidence.append(
                dict(
                    source=self.name,
                    description="Non-standard HTTP headers detected",
                    raw={"headers": list(seen)},
                    confidence=0.60,
                )
            )

        return findings
