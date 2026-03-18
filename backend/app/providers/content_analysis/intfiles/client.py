# backend/app/providers/content_analysis/intfiles/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.LOW
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_intfiles.py (MIT licensed)
# Copyright (c) Steve Micallef.
import re
from typing import Any

_URL_RE = re.compile(r'https?://[^\s"\'<>]+', re.IGNORECASE)

_INTERESTING_EXTS = frozenset(
    [
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".7z",
        ".rar",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".sql",
        ".db",
        ".sqlite",
        ".bak",
        ".backup",
        ".key",
        ".pem",
        ".crt",
        ".pfx",
        ".p12",
        ".env",
        ".cfg",
        ".conf",
        ".config",
        ".ini",
        ".log",
        ".csv",
        ".json",
        ".xml",
        ".sh",
        ".bat",
        ".ps1",
        ".py",
        ".rb",
        ".php",
    ]
)


from backend.app.providers.base.client import BaseProviderClient


class IntfilesProvider(BaseProviderClient):
    name = "intfiles"

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
                lower = url_clean.lower()
                ext = ""
                for e in _INTERESTING_EXTS:
                    if lower.endswith(e) or (e + "?") in lower or (e + "#") in lower:
                        ext = e
                        break
                if not ext:
                    continue
                if url_clean in seen:
                    continue
                seen.add(url_clean)
                findings.append(
                    dict(
                        provider=self.name,
                        category="interesting_file",
                        title="Interesting file link found",
                        description=f"Link to potentially sensitive file ({ext}): {url_clean}",
                        entity_type="url",
                        entity_value=url_clean,
                        confidence=0.65,
                        tags=[
                            "content_analysis",
                            "intfiles",
                            "passive",
                            ext.lstrip("."),
                        ],
                    )
                )
        if findings:
            evidence.append(
                dict(
                    source=self.name,
                    description="Interesting file links found in content",
                    raw={"count": len(findings)},
                    confidence=0.65,
                )
            )

        return findings
