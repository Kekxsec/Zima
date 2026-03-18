# backend/app/providers/content_analysis/filemeta/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.LOW
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_filemeta.py (MIT licensed)
# Copyright (c) Steve Micallef.
import re
from typing import Any

# Patterns that suggest embedded metadata
_META_PATTERNS = [
    ("Author", re.compile(r"(?:Author|Creator|Producer):\s*([^\r\n<]{3,80})", re.I)),
    (
        "Creation Date",
        re.compile(r"(?:CreationDate|Created|Date Created):\s*([^\r\n<]{3,40})", re.I),
    ),
    (
        "Software",
        re.compile(r"(?:Producer|Creator Tool|Generator):\s*([^\r\n<]{3,80})", re.I),
    ),
    (
        "GPS Coordinates",
        re.compile(r"GPS(?:Latitude|Longitude|Position):\s*([^\r\n<]{3,40})", re.I),
    ),
    (
        "OS/Platform",
        re.compile(r"(?:Operating System|Platform):\s*([^\r\n<]{3,40})", re.I),
    ),
]

# Look for common metadata disclosure in HTML meta tags
_HTML_META_RE = re.compile(
    r'<meta\s+(?:name|property)=["\']([^"\']{2,40})["\'][^>]*content=["\']([^"\']{2,200})["\']',
    re.I,
)


from backend.app.providers.base.client import BaseProviderClient


class FilemetaProvider(BaseProviderClient):
    name = "filemeta"

    async def get_file_metadata(self, content: str) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen: set[str] = set()

        if not content:
            return findings
        # Embedded metadata patterns
        for label, pattern in _META_PATTERNS:
            m = pattern.search(content)
            if not m:
                continue
            value = m.group(1).strip()
            key = f"{label}:{value}"
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                dict(
                    provider=self.name,
                    category="information_disclosure",
                    title=f"File metadata found: {label}",
                    description=f"Metadata field '{label}' contains: {value}",
                    entity_type="web_content",
                    entity_value=value,
                    confidence=0.65,
                    tags=["content_analysis", "filemeta", "metadata", "passive"],
                )
            )
        # HTML meta tags
        for name, content in _HTML_META_RE.findall(content):
            key = f"meta:{name.lower()}:{content[:40]}"
            if key in seen:
                continue
            seen.add(key)
            findings.append(
                dict(
                    provider=self.name,
                    category="information_disclosure",
                    title=f"HTML meta tag: {name}",
                    description=f"HTML meta tag '{name}' = '{content[:80]}'",
                    entity_type="web_content",
                    entity_value=content[:200],
                    confidence=0.60,
                    tags=["content_analysis", "filemeta", "html_meta", "passive"],
                )
            )
        if findings:
            evidence.append(
                dict(
                    source=self.name,
                    description="File/page metadata extracted from content",
                    raw={"count": len(findings)},
                    confidence=0.65,
                )
            )

        return findings
