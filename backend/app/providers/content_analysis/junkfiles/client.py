# backend/app/providers/content_analysis/junkfiles/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.LOW
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_junkfiles.py (MIT licensed)
# Copyright (c) Steve Micallef.
import re
from typing import Any

_URL_RE = re.compile(r'https?://[^\s"\'<>]+', re.IGNORECASE)

_JUNK_EXTS = frozenset(
    [
        ".tmp",
        ".temp",
        ".bak",
        ".old",
        ".orig",
        ".copy",
        ".swp",
        ".swo",
        ".~",
    ]
)

_JUNK_PATTERNS = [
    re.compile(r"~\$"),  # Office temp files
    re.compile(r"\.swp$", re.I),  # vim swap
    re.compile(r"\.bak\b", re.I),  # backups
    re.compile(r"\.tmp\b", re.I),  # temp files
    re.compile(r"Thumbs\.db", re.I),  # Windows thumbnail cache
    re.compile(r"\.DS_Store", re.I),  # macOS metadata
    re.compile(r"desktop\.ini", re.I),  # Windows desktop settings
    re.compile(r"backup.*\.(zip|tar|gz|sql)", re.I),
]


from backend.app.providers.base.client import BaseProviderClient


class JunkfilesProvider(BaseProviderClient):
    name = "junkfiles"

    async def find_interesting_files(
        self, *, content: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen: set[str] = set()

        _inputs: list[tuple[str, str]] = []
        if content is not None:
            _inputs.append(("content", content))
        if url is not None:
            _inputs.append(("url", url))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"web_content", "binary_content"}:
                continue
            if not _value:
                continue
            for url in _URL_RE.findall(_value):
                url_clean = url.rstrip(".,;)'\"")
                if url_clean in seen:
                    continue
                if any(p.search(url_clean) for p in _JUNK_PATTERNS):
                    seen.add(url_clean)
                    findings.append(
                        dict(
                            provider=self.name,
                            category="information_disclosure",
                            title="Junk/temporary file exposed",
                            description=f"Link to temporary or junk file found: {url_clean}",
                            entity_type="url",
                            entity_value=url_clean,
                            confidence=0.70,
                            tags=["content_analysis", "junkfiles", "passive"],
                        )
                    )
        if findings:
            evidence.append(
                dict(
                    source=self.name,
                    description="Junk/temporary files found in content",
                    raw={"count": len(findings)},
                    confidence=0.70,
                )
            )

        return findings
