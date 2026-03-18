# backend/app/providers/content_analysis/email_extractor/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_email.py (MIT licensed)
# Copyright (c) Steve Micallef.
import re
from typing import Any

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")


from backend.app.providers.base.client import BaseProviderClient


class EmailProvider(BaseProviderClient):
    name = "email"

    async def extract_emails(
        self, *, content: str | None = None, email: str | None = None
    ) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen: set[str] = set()

        _inputs: list[tuple[str, str]] = []
        if content is not None:
            _inputs.append(("content", content))
        if email is not None:
            _inputs.append(("email", email))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"web_content", "binary_content"}:
                continue
            if not _value:
                continue
            matches = _EMAIL_RE.findall(_value)
            unique = {m.lower() for m in matches}
            for addr in sorted(unique):
                if addr in seen:
                    continue
                seen.add(addr)
                findings.append(
                    dict(
                        provider=self.name,
                        category="identity_exposure",
                        title="Email address found in content",
                        description=f"Email address {addr} extracted from content",
                        entity_type="email",
                        entity_value=addr,
                        confidence=0.72,
                        tags=["content_analysis", "email", "passive"],
                    )
                )
            if unique:
                evidence.append(
                    dict(
                        source=self.name,
                        description="Email addresses extracted from content",
                        raw={"count": len(unique)},
                        confidence=0.72,
                    )
                )

        return findings
