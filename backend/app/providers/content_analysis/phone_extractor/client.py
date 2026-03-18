# backend/app/providers/content_analysis/phone_extractor/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_phone.py (MIT licensed)
# Copyright (c) Steve Micallef.
import re
from typing import Any

# Loose international phone pattern: optional +, 7-15 digits with separators
_PHONE_RE = re.compile(r"(?<!\w)(\+?(?:[0-9][ \-.]?){7,14}[0-9])(?!\w)")


from backend.app.providers.base.client import BaseProviderClient


class PhoneProvider(BaseProviderClient):
    name = "phone"

    async def extract_phones(
        self, *, content: str | None = None, phone_number: str | None = None
    ) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen: set[str] = set()

        _inputs: list[tuple[str, str]] = []
        if content is not None:
            _inputs.append(("content", content))
        if phone_number is not None:
            _inputs.append(("phone_number", phone_number))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"web_content", "binary_content"}:
                continue
            if not _value:
                continue
            for match in _PHONE_RE.findall(_value):
                normalized = re.sub(r"[^\d+]", "", match)
                if len(normalized.lstrip("+")) < 7:
                    continue
                if normalized in seen:
                    continue
                seen.add(normalized)
                findings.append(
                    dict(
                        provider=self.name,
                        category="identity_exposure",
                        title="Phone number found in content",
                        description=f"Phone number pattern detected: {normalized}",
                        entity_type="phone",
                        entity_value=normalized,
                        confidence=0.55,
                        tags=["content_analysis", "phone", "passive"],
                    )
                )
        if findings:
            evidence.append(
                dict(
                    source=self.name,
                    description="Phone numbers detected in content",
                    raw={"count": len(findings)},
                    confidence=0.55,
                )
            )

        return findings
