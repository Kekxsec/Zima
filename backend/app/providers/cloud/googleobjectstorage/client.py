# backend/app/providers/cloud/googleobjectstorage/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---

# Adapted from SpiderFoot module: modules/sfp_googleobjectstorage.py (MIT licensed)

GCS_BASE = "https://storage.googleapis.com"
BUCKET_MUTATIONS = [
    "{name}",
    "{name}-backup",
    "{name}-data",
    "{name}-dev",
    "{name}-prod",
    "{name}-staging",
    "{name}-assets",
    "{name}-media",
    "{name}-files",
    "{name}-public",
]


from backend.app.providers.base.client import BaseProviderClient


class GoogleobjectstorageProvider(BaseProviderClient):
    name = "googleobjectstorage"

    def __init__(self, timeout_seconds: int = 10):
        self._timeout_seconds = timeout_seconds

    async def check_bucket(self, domain: str) -> list[dict[str, Any]]:
        findings, evidence = [], []
        seen: set[str] = set()
        val = domain.strip().lower()
        base_name = val.split(".")[0]
        for pattern in BUCKET_MUTATIONS:
            bucket = pattern.format(name=base_name)
            if bucket in seen:
                continue
            seen.add(bucket)
            url = f"{GCS_BASE}/{bucket}"
            try:
                resp = await self._get(url, timeout=self._timeout_seconds)
            except Exception:
                return findings
            if resp.status_code == 200:
                findings.append(
                    dict(
                        provider=self.name,
                        category="cloud_storage",
                        title=f"GCS open bucket: {bucket}",
                        description=f"Google Cloud Storage bucket {bucket} is publicly accessible (200 OK)",
                        entity_type="domain",
                        entity_value=val,
                        confidence=0.90,
                        tags=["gcs", "cloud_storage", "open_bucket", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Open GCS bucket for {val}",
                        raw={"bucket": bucket, "url": url, "status": 200},
                        confidence=0.90,
                    )
                )
            elif resp.status_code == 403:
                findings.append(
                    dict(
                        provider=self.name,
                        category="cloud_storage",
                        title=f"GCS bucket exists: {bucket}",
                        description=f"Google Cloud Storage bucket {bucket} exists but is access-controlled (403)",
                        entity_type="domain",
                        entity_value=val,
                        confidence=0.75,
                        tags=["gcs", "cloud_storage", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"GCS bucket existence for {val}",
                        raw={"bucket": bucket, "url": url, "status": 403},
                        confidence=0.75,
                    )
                )
        return findings
