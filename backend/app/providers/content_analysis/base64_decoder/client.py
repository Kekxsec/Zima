# backend/app/providers/content_analysis/base64_decoder/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_base64.py (MIT licensed)
# Copyright (c) Steve Micallef.
import base64
import re
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class Base64DecoderProvider(BaseProviderClient):
    name = "base64_decoder"
    _pattern = re.compile(r"([A-Za-z0-9+\/]+={1,2})")

    def __init__(self, min_length: int = 10):
        self._min_length = min_length

    async def decode_base64(
        self,
        *,
        email: str | None = None,
        url: str | None = None,
        username: str | None = None,
        content: str | None = None,
    ) -> list[dict[str, Any]]:
        min_length = int(self._min_length)
        min_length = max(4, min(min_length, 4096))
        findings = []
        evidence = []
        seen = set()

        _inputs: list[tuple[str, str]] = []
        if email is not None:
            _inputs.append(("email", email))
        if url is not None:
            _inputs.append(("url", url))
        if username is not None:
            _inputs.append(("username", username))
        if content is not None:
            _inputs.append(("content", content))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"url", "web_content"}:
                continue
            decoded_input = urllib.parse.unquote(_value or "")
            matches = self._pattern.findall(decoded_input)
            for match in matches:
                if len(match) < min_length:
                    continue
                caps = sum(1 for c in match if c.isupper())
                if caps < (min_length / 4):
                    continue
                try:
                    decoded = base64.b64decode(match, validate=False).decode("utf-8")
                except Exception:
                    return findings
                if not decoded.strip():
                    continue
                key = (match, decoded)
                if key in seen:
                    continue
                seen.add(key)
                decoded_clean = decoded.strip()[:512]
                entity_type = "username"
                if decoded_clean.startswith(("http://", "https://")):
                    entity_type = "url"
                elif "@" in decoded_clean:
                    entity_type = "email"
                findings.append(
                    dict(
                        provider=self.name,
                        category="identity_exposure",
                        title="Base64 data discovered",
                        description="Potentially interesting Base64-encoded string identified and decoded",
                        entity_type=entity_type,
                        entity_value=decoded_clean,
                        confidence=0.6,
                        tags=["content_analysis", "base64", "passive"],
                    )
                )

            if matches:
                evidence.append(
                    dict(
                        source=self.name,
                        description="Base64 token scan",
                        raw={"candidate_count": len(matches)},
                        confidence=0.6,
                    )
                )

        return findings
