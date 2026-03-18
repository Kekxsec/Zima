# backend/app/providers/content_analysis/creditcard_extractor/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_creditcard.py (MIT licensed)
# Copyright (c) Steve Micallef.
import re
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class CreditCardProvider(BaseProviderClient):
    name = "creditcard"
    _pattern = re.compile(r"\b(?:\d[ -]*?){13,19}\b")

    async def find_credit_cards(self, content: str) -> list[dict[str, Any]]:
        include_full = False
        findings = []
        evidence = []
        seen = set()
        if not content:
            return findings
        matches = self._pattern.findall(content)
        valid_cards = []
        for match in matches:
            cleaned = re.sub(r"[^0-9]", "", match)
            if len(cleaned) < 13 or len(cleaned) > 19:
                continue
            if not self._passes_luhn(cleaned):
                continue
            valid_cards.append(cleaned)
        for card in sorted(set(valid_cards)):
            value = card if include_full else self._mask(card)
            if value in seen:
                continue
            seen.add(value)
            findings.append(
                dict(
                    provider=self.name,
                    category="identity_exposure",
                    title="Potential payment card number detected",
                    description="A Luhn-valid payment card number pattern was identified in supplied content",
                    entity_type="credit_card",
                    entity_value=value,
                    confidence=0.67,
                    tags=[
                        "content_analysis",
                        "creditcard",
                        "passive",
                        "sensitive_data",
                    ],
                )
            )
        if valid_cards:
            evidence.append(
                dict(
                    source=self.name,
                    description="Credit card scan completed",
                    raw={"detected_count": len(set(valid_cards))},
                    confidence=0.67,
                )
            )
        return findings

    @staticmethod
    def _passes_luhn(number: str) -> bool:
        total = 0
        reverse_digits = number[::-1]
        for idx, ch in enumerate(reverse_digits):
            digit = int(ch)
            if idx % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            total += digit
        return total % 10 == 0

    @staticmethod
    def _mask(number: str) -> str:
        if len(number) <= 8:
            return number
        return f"{number[:4]}{'*' * (len(number) - 8)}{number[-4:]}"
