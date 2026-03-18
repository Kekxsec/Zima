# backend/app/providers/cloud/azureblobstorage/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_azureblobstorage.py (MIT licensed)
# Copyright (c) Steve Micallef.
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class AzureBlobStorageProvider(BaseProviderClient):
    name = "azureblobstorage"

    def __init__(self, timeout_seconds: int = 10):
        self._timeout_seconds = timeout_seconds

    async def check_bucket(
        self, *, domain: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        suffixes_raw = "test,dev,web,beta,bucket,space,files,content,data,prod,staging,production,stage,app,media,development"
        max_candidates = 40
        max_candidates = max(1, min(max_candidates, 200))
        suffixes = [s.strip() for s in suffixes_raw.split(",") if s.strip()]

        findings = []
        evidence = []
        seen = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if url is not None:
            _inputs.append(("url", url))
        for _entity_type, _value in _inputs:
            candidates = self._build_candidates(_entity_type, _value, suffixes)
            for bucket_host in candidates[:max_candidates]:
                if bucket_host in seen:
                    continue
                seen.add(bucket_host)
                url = f"https://{bucket_host}"
                status = await self._probe(url)
                if status is None:
                    continue
                # 200/403 are strong indicators of existing bucket endpoints.
                if status not in {200, 403}:
                    continue
                findings.append(
                    dict(
                        provider=self.name,
                        category="attack_surface",
                        title="Potential Azure Blob storage bucket",
                        description=f"Azure Blob endpoint responded with HTTP {status}: {bucket_host}",
                        entity_type="hostname",
                        entity_value=bucket_host,
                        confidence=0.65,
                        tags=["cloud_storage", "azure_blob", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Azure Blob probe result for {bucket_host}",
                        raw={"url": url, "status_code": status},
                        confidence=0.65,
                    )
                )
        return findings

    def _build_candidates(
        self, entity_type: str, value: str, suffixes: list[str]
    ) -> list[str]:
        candidates = []
        if entity_type == "url":
            host = urllib.parse.urlparse(value.strip()).hostname or ""
            if host.endswith(".blob.core.windows.net"):
                candidates.append(host.lower())
            return candidates
        if entity_type != "domain":
            return candidates

        domain = value.strip().lower()
        if not domain:
            return candidates
        base = domain.replace(".", "")
        parts = domain.split(".")
        keyword = parts[-2] if len(parts) >= 2 else base
        for seed in [base, keyword]:
            if not seed:
                continue
            candidates.append(f"{seed}.blob.core.windows.net")
            for suffix in suffixes:
                candidates.append(f"{seed}{suffix}.blob.core.windows.net")
        return candidates

    async def _probe(self, url: str) -> int | None:
        try:
            response = await self._get(url, timeout=self._timeout_seconds)
        except Exception as exc:
            # Treat transport failures as soft misses in this enumerator.
            if isinstance(exc, TimeoutError):
                return None
            return None

        if response.status_code == 429:
            raise ProviderError(
                message="Azure Blob probe rate limited request",
                retryable=True,
            )
        if response.status_code >= 500:
            return None
        return response.status_code
