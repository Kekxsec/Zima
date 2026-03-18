# backend/app/providers/content_analysis/hashes_extractor/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_hashes.py (MIT licensed)
# Copyright (c) Steve Micallef.
import re
from typing import Any

_MD5_RE = re.compile(r"\b[0-9a-fA-F]{32}\b")
_SHA1_RE = re.compile(r"\b[0-9a-fA-F]{40}\b")
_SHA256_RE = re.compile(r"\b[0-9a-fA-F]{64}\b")
_SHA512_RE = re.compile(r"\b[0-9a-fA-F]{128}\b")


from backend.app.providers.base.client import BaseProviderClient


class HashesProvider(BaseProviderClient):
    name = "hashes"

    async def extract_hashes(
        self, *, content: str | None = None, hash_value: str | None = None
    ) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen: set[str] = set()

        _inputs: list[tuple[str, str]] = []
        if content is not None:
            _inputs.append(("content", content))
        if hash_value is not None:
            _inputs.append(("hash_value", hash_value))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"web_content", "binary_content"}:
                continue
            if not _value:
                continue

            text = _value
            # Order matters: match longer patterns first to avoid subsets
            for pattern, hash_type in [
                (_SHA512_RE, "SHA-512"),
                (_SHA256_RE, "SHA-256"),
                (_SHA1_RE, "SHA-1"),
                (_MD5_RE, "MD5"),
            ]:
                for match in pattern.findall(text):
                    h = match.lower()
                    if h in seen:
                        continue
                    seen.add(h)
                    findings.append(
                        dict(
                            provider=self.name,
                            category="content_analysis",
                            title=f"{hash_type} hash found in content",
                            description=f"{hash_type} hash detected: {h}",
                            entity_type="hash",
                            entity_value=h,
                            confidence=0.68,
                            tags=[
                                "content_analysis",
                                "hash",
                                hash_type.lower().replace("-", ""),
                                "passive",
                            ],
                        )
                    )
                # Remove matched text to avoid sub-pattern double-matching
                text = pattern.sub("", text)

        if findings:
            evidence.append(
                dict(
                    source=self.name,
                    description="Cryptographic hashes detected in content",
                    raw={"count": len(findings)},
                    confidence=0.68,
                )
            )

        return findings
