# backend/app/providers/content_analysis/webanalytics/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_webanalytics.py (MIT licensed)
# Copyright (c) Steve Micallef.
import re
from typing import Any

# Analytics tracker patterns: (label, regex)
_TRACKERS = [
    ("Google Analytics (UA)", re.compile(r"\bua-\d{4,10}-\d{1,4}\b", re.I)),
    ("Google Analytics (GA4)", re.compile(r"\bG-[A-Z0-9]{8,12}\b", re.I)),
    ("Google Tag Manager", re.compile(r"\bGTM-[A-Z0-9]{4,8}\b", re.I)),
    (
        "Facebook Pixel",
        re.compile(r"fbq\s*\(|connect\.facebook\.net/[a-z_]+/fbevents", re.I),
    ),
    ("Hotjar", re.compile(r"hotjar\.com|hjid\s*:", re.I)),
    ("Mixpanel", re.compile(r"mixpanel\.init\s*\(", re.I)),
    ("Segment", re.compile(r"analytics\.identify\s*\(|cdn\.segment\.com", re.I)),
    ("Amplitude", re.compile(r"amplitude\.init\s*\(|amplitude\.getInstance", re.I)),
    ("Matomo/Piwik", re.compile(r"matomo\.js|piwik\.js|_paq\.push", re.I)),
    ("Yandex.Metrika", re.compile(r"mc\.yandex\.ru/metrika|ym\s*\(", re.I)),
]


from backend.app.providers.base.client import BaseProviderClient


class WebanalyticsProvider(BaseProviderClient):
    name = "webanalytics"

    async def detect_analytics(self, content: str) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen: set[str] = set()

        if not content:
            return findings
        for label, pattern in _TRACKERS:
            match = pattern.search(content)
            if not match:
                continue
            key = label
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                dict(
                    provider=self.name,
                    category="tracking",
                    title=f"Web analytics tracker detected: {label}",
                    description=f"{label} tracker code found in page content",
                    entity_type="web_content",
                    entity_value=label,
                    confidence=0.80,
                    tags=["content_analysis", "webanalytics", "tracking", "passive"],
                )
            )
        if findings:
            evidence.append(
                dict(
                    source=self.name,
                    description="Analytics trackers identified in content",
                    raw={"trackers": list(seen)},
                    confidence=0.80,
                )
            )

        return findings
