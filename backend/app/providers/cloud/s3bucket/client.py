# backend/app/providers/cloud/s3bucket/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_s3bucket.py (MIT licensed)

_BUCKET_MUTATIONS = [
    "{name}",
    "{name}-backup",
    "{name}-data",
    "{name}-dev",
    "{name}-prod",
    "{name}-static",
    "{name}-assets",
    "backup-{name}",
    "dev-{name}",
    "data-{name}",
]


from backend.app.providers.base.client import BaseProviderClient


class S3bucketProvider(BaseProviderClient):
    name = "s3bucket"

    def __init__(self, timeout_seconds: int = 10):
        self._timeout_seconds = timeout_seconds

    async def check_bucket(self, domain: str) -> list[dict[str, Any]]:
        findings, evidence = [], []
        val = domain.strip()
        base_name = val.replace(".", "-").lower()
        found = []
        for template in _BUCKET_MUTATIONS[:5]:  # limit checks
            bucket_name = template.format(name=base_name)
            bucket_url = f"https://{bucket_name}.s3.amazonaws.com"
            try:
                resp = await self._get(bucket_url, timeout=self._timeout_seconds)
                if resp.status_code in {200, 403}:
                    is_open = resp.status_code == 200
                    found.append((bucket_name, is_open))
            except Exception:
                pass
        for bucket_name, is_open in found:
            sev = "removed_severity" if is_open else "removed_severity"
            findings.append(
                dict(
                    provider=self.name,
                    category="cloud_storage",
                    title=f"S3 bucket: {bucket_name}",
                    description=f"S3 bucket found: {bucket_name}.s3.amazonaws.com"
                    + (
                        " (publicly accessible)"
                        if is_open
                        else " (exists, access denied)"
                    ),
                    severity=sev,
                    entity_type="domain",
                    entity_value=val,
                    confidence=0.75,
                    tags=["s3bucket", "aws", "cloud_storage", "passive"],
                )
            )
        if found:
            evidence.append(
                dict(
                    source=self.name,
                    description=f"S3 buckets for {val}",
                    raw={"count": len(found)},
                    confidence=0.75,
                )
            )
        return findings
