# backend/app/providers/content_analysis/iban_extractor/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_iban.py (MIT licensed)
# Copyright (c) Steve Micallef.
import re
from typing import Any

# IBAN: 2 letter country code + 2 check digits + up to 30 alphanumeric chars
_IBAN_RE = re.compile(r"\b([A-Z]{2}[0-9]{2}[A-Z0-9]{4,30})\b")


from backend.app.providers.base.client import BaseProviderClient


class IbanProvider(BaseProviderClient):
    name = "iban"

    async def extract_ibans(self, content: str) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen: set[str] = set()

        if not content:
            return findings
        for match in _IBAN_RE.findall(content):
            candidate = match.replace(" ", "").upper()
            if candidate in seen:
                continue
            if not self._passes_luhn(candidate):
                continue
            seen.add(candidate)
            masked = self._mask(candidate)
            findings.append(
                dict(
                    provider=self.name,
                    category="identity_exposure",
                    title="IBAN detected in content",
                    description=f"Luhn-valid IBAN pattern detected: {masked}",
                    entity_type="iban",
                    entity_value=masked,
                    confidence=0.73,
                    tags=["content_analysis", "iban", "sensitive_data", "passive"],
                )
            )
        if findings:
            evidence.append(
                dict(
                    source=self.name,
                    description="IBAN numbers detected in content",
                    raw={"count": len(findings)},
                    confidence=0.73,
                )
            )

        return findings

    @staticmethod
    def _passes_luhn(iban: str) -> bool:
        """ISO 7064 MOD-97-10 check."""
        rearranged = iban[4:] + iban[:4]
        numeric = ""
        for ch in rearranged:
            if ch.isdigit():
                numeric += ch
            elif ch.isalpha():
                numeric += str(ord(ch.upper()) - 55)
            else:
                return False
        try:
            return int(numeric) % 97 == 1
        except ValueError:
            return False

    @staticmethod
    def _mask(iban: str) -> str:
        if len(iban) <= 8:
            return iban
        return f"{iban[:4]}{'*' * (len(iban) - 8)}{iban[-4:]}"
