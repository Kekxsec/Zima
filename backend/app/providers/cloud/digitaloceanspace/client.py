# backend/app/providers/cloud/digitaloceanspace/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_digitaloceanspace.py (MIT licensed)

_REGIONS = ["nyc3", "sgp1", "ams3", "fra1", "sfo2", "sfo3", "blr1", "tor1", "syd1"]


from backend.app.providers.base.client import BaseProviderClient


class DigitaloceanspaceProvider(BaseProviderClient):
    name = "digitaloceanspace"

    def __init__(self, timeout_seconds: int = 10):
        self._timeout_seconds = timeout_seconds

    async def check_bucket(self, domain: str) -> list[dict[str, Any]]:
        findings, evidence = [], []
        val = domain.strip()
        # Generate bucket name candidates from domain
        base = val.replace(".", "-").replace("_", "-").lower()
        candidates = [base, base.replace("-", ""), val.split(".")[0]]
        found = []
        for candidate in candidates:
            for region in _REGIONS[:3]:  # limit checks
                bucket_url = f"https://{candidate}.{region}.digitaloceanspaces.com"
                try:
                    resp = await self._get(bucket_url, timeout=self._timeout_seconds)
                    if resp.status_code in {200, 403}:
                        open_access = resp.status_code == 200
                        found.append((candidate, region, open_access))
                except Exception:
                    pass
        for bucket, region, is_open in found:
            sev = "removed_severity" if is_open else "removed_severity"
            findings.append(
                dict(
                    provider=self.name,
                    category="cloud_storage",
                    title=f"DO Space: {bucket}.{region}",
                    description=f"DigitalOcean Space found: {bucket}.{region}.digitaloceanspaces.com"
                    + (
                        " (publicly accessible)"
                        if is_open
                        else " (exists, access denied)"
                    ),
                    severity=sev,
                    entity_type="domain",
                    entity_value=val,
                    confidence=0.70,
                    tags=["digitalocean", "cloud_storage", "passive"],
                )
            )
        if found:
            evidence.append(
                dict(
                    source=self.name,
                    description=f"DO Spaces found for {val}",
                    raw={"count": len(found)},
                    confidence=0.70,
                )
            )
        return findings
