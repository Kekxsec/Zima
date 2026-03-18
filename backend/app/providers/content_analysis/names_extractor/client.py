# backend/app/providers/content_analysis/names_extractor/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_names.py (MIT licensed)
# Copyright (c) Steve Micallef.
import re
from typing import Any

# Pattern for "Firstname Lastname" capitalized words (2-3 words)
_NAME_RE = re.compile(r"\b([A-Z][a-z]{1,20}(?:\s+[A-Z][a-z]{1,20}){1,2})\b")

# Common false-positive words to skip
_SKIP = frozenset(
    [
        "January",
        "February",
        "March",
        "April",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
        "United States",
        "United Kingdom",
        "New York",
        "Los Angeles",
        "The Internet",
        "The Web",
    ]
)


from backend.app.providers.base.client import BaseProviderClient


class NamesProvider(BaseProviderClient):
    name = "names"

    async def extract_names(
        self, *, content: str | None = None, name: str | None = None
    ) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen: set[str] = set()

        _inputs: list[tuple[str, str]] = []
        if content is not None:
            _inputs.append(("content", content))
        if name is not None:
            _inputs.append(("name", name))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"web_content", "binary_content"}:
                continue
            if not _value:
                continue
            for match in _NAME_RE.findall(_value):
                name = match.strip()
                if name in _SKIP or name in seen:
                    continue
                seen.add(name)
                findings.append(
                    dict(
                        provider=self.name,
                        category="identity_exposure",
                        title="Human name found in content",
                        description=f"Potential human name detected: {name}",
                        entity_type="human_name",
                        entity_value=name,
                        confidence=0.45,
                        tags=["content_analysis", "names", "passive"],
                    )
                )
        if findings:
            evidence.append(
                dict(
                    source=self.name,
                    description="Human names detected in content",
                    raw={"count": len(findings)},
                    confidence=0.45,
                )
            )

        return findings
