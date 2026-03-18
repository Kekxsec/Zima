# backend/app/providers/domain/tldsearch/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---

# Adapted from SpiderFoot module: modules/sfp_tldsearch.py (MIT licensed)

# Public list of TLDs from IANA
TLDS_URL = "https://data.iana.org/TLD/tlds-alpha-by-domain.txt"


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class TldsearchProvider(BaseProviderClient):
    name = "tldsearch"

    def __init__(self, timeout_seconds: int = 30):
        self._timeout_seconds = timeout_seconds

    async def get_tld_info(self, domain: str) -> list[dict[str, Any]]:
        # Fetch TLD list
        try:
            resp = await self._get(TLDS_URL, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="TLD list fetch failed", retryable=True
            ) from exc
        if resp.status_code != 200:
            raise ProviderError(message="TLD list unexpected response", retryable=False)
        content = (
            resp.content
            if isinstance(resp.content, str)
            else resp.content.decode("utf-8", errors="replace")
        )
        tlds = [
            line.strip().lower()
            for line in content.splitlines()
            if line.strip() and not line.startswith("#")
        ]

        findings, evidence = [], []
        val = domain.strip().lower()
        # Extract the base name (without TLD)
        parts = val.split(".")
        if len(parts) < 2:
            return findings
        base = parts[0]
        current_tld = parts[-1]
        matches = []
        for tld in tlds:
            if tld == current_tld:
                continue
            candidate = f"{base}.{tld}"
            matches.append(candidate)
            if len(matches) >= 20:
                break
        if matches:
            findings.append(
                dict(
                    provider=self.name,
                    category="domain_permutation",
                    title=f"TLD variants: {val}",
                    description=f"Domain {val} has potential TLD variants across {len(tlds)} TLDs",
                    entity_type="domain",
                    entity_value=val,
                    confidence=0.55,
                    tags=["tldsearch", "domain", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"TLD permutations for {val}",
                    raw={
                        "base": base,
                        "tld_count": len(tlds),
                        "sample_variants": matches[:10],
                    },
                    confidence=0.55,
                )
            )
        return findings
