# backend/app/providers/content_analysis/binstring/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_binstring.py (MIT licensed)
# Copyright (c) Steve Micallef.
import string
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class BinStringProvider(BaseProviderClient):
    name = "binstring"

    def __init__(
        self,
        min_word_size: int = 5,
        max_words: int = 100,
        filter_chars: str = "#}{|%^&*()=+,;[]~",
    ):
        self._min_word_size = min_word_size
        self._max_words = max_words
        self._filter_chars = filter_chars

    async def find_strings(self, content: str) -> list[dict[str, Any]]:
        min_word_size = int(self._min_word_size)
        max_words = int(self._max_words)
        filter_chars = str(self._filter_chars)
        min_word_size = max(2, min(min_word_size, 128))
        max_words = max(1, min(max_words, 2000))

        findings = []
        evidence = []
        seen = set()
        words = self._extract_strings(
            content or "", min_word_size, max_words, filter_chars
        )
        for word in words:
            if word in seen:
                continue
            seen.add(word)
            findings.append(
                dict(
                    provider=self.name,
                    category="identity_exposure",
                    title="String extracted from binary content",
                    description="Printable string discovered from binary content analysis",
                    entity_type="web_content",
                    entity_value=word[:512],
                    confidence=0.55,
                    tags=["content_analysis", "binary_strings", "passive"],
                )
            )
        if words:
            evidence.append(
                dict(
                    source=self.name,
                    description="Binary string extraction summary",
                    raw={"word_count": len(words)},
                    confidence=0.55,
                )
            )

        return findings

    @staticmethod
    def _extract_strings(
        content: str, min_word_size: int, max_words: int, filter_chars: str
    ) -> list[str]:
        words = []
        token = ""
        for char in content:
            if len(words) >= max_words:
                break
            if char in string.printable and char not in string.whitespace:
                token += char
                continue
            if len(token) >= min_word_size:
                if filter_chars and any(fc in token for fc in filter_chars):
                    token = ""
                    continue
                words.append(token)
            token = ""
        if len(token) >= min_word_size and len(words) < max_words:
            if not filter_chars or not any(fc in token for fc in filter_chars):
                words.append(token)
        return words
