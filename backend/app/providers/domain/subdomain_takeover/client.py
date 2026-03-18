# backend/app/providers/domain/subdomain_takeover/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---

# Adapted from SpiderFoot module: modules/sfp_subdomain_takeover.py (MIT licensed)

FINGERPRINTS_URL = "https://raw.githubusercontent.com/EdOverflow/can-i-take-over-xyz/master/fingerprints.json"


from backend.app.providers.base.client import BaseProviderClient


class SubdomainTakeoverProvider(BaseProviderClient):
    name = "subdomain_takeover"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def check_takeover(self, domain: str) -> list[dict[str, Any]]:
        findings, evidence = [], []
        # Fetch fingerprints
        fingerprints = await self._get(
            FINGERPRINTS_URL, label="SubdomainTakeover", timeout=self._timeout_seconds
        )
        if not isinstance(fingerprints, list):
            return findings
        val = domain.strip()
        for fp in fingerprints:
            if not isinstance(fp, dict):
                continue
            fingerprint = str(fp.get("fingerprint", "")).strip()
            service = str(fp.get("service", "")).strip()
            vulnerable = fp.get("vulnerable", False)
            if not fingerprint or not vulnerable:
                continue
            if fingerprint.lower() in val.lower():
                findings.append(
                    dict(
                        provider=self.name,
                        category="vulnerability",
                        title=f"Subdomain takeover: {service}",
                        description=f"Potential subdomain takeover for {domain}: matches {service} fingerprint",
                        entity_type="domain",
                        entity_value=val,
                        confidence=0.75,
                        tags=["subdomain_takeover", "vulnerability", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Takeover fingerprint match for {val}",
                        raw={"service": service, "fingerprint": fingerprint[:50]},
                        confidence=0.75,
                    )
                )
                break
        return findings
