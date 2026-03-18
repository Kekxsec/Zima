# backend/app/providers/content_analysis/ethereum_extractor/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_ethereum.py (MIT licensed)
# Copyright (c) Steve Micallef.
import re
from typing import Any

# Ethereum address: 0x followed by 40 hex chars
_ETH_RE = re.compile(r"\b(0x[0-9a-fA-F]{40})\b")


from backend.app.providers.base.client import BaseProviderClient


class EthereumProvider(BaseProviderClient):
    name = "ethereum"

    async def extract_ethereum(self, content: str) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen: set[str] = set()

        if not content:
            return findings
        for match in _ETH_RE.findall(content):
            addr = match.lower()
            if addr in seen:
                continue
            seen.add(addr)
            findings.append(
                dict(
                    provider=self.name,
                    category="cryptocurrency",
                    title="Ethereum address found in content",
                    description=f"Ethereum address detected: {addr}",
                    entity_type="ethereum_address",
                    entity_value=addr,
                    confidence=0.72,
                    tags=["content_analysis", "ethereum", "cryptocurrency", "passive"],
                )
            )
        if findings:
            evidence.append(
                dict(
                    source=self.name,
                    description="Ethereum addresses detected in content",
                    raw={"count": len(findings)},
                    confidence=0.72,
                )
            )

        return findings
