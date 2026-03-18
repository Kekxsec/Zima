# backend/app/providers/search/archiveorg/client.py
from __future__ import annotations

import urllib.parse

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_archiveorg.py (MIT licensed)
# Copyright (c) Steve Micallef.
from datetime import datetime, timedelta
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ArchiveOrgProvider(BaseProviderClient):
    name = "archiveorg"
    base_url = "https://archive.org/wayback/available"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def search_archives(self, url: str) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        days_back = [30, 60, 90]
        normalized_days = self._normalize_days(days_back)
        seen_urls = set()

        target_url = url.strip()
        if not target_url:
            return findings

        for days in normalized_days:
            payload = await self._query(target_url, days)
            snapshot_url = self._extract_snapshot_url(payload)
            if not snapshot_url:
                continue
            if snapshot_url in seen_urls:
                continue
            seen_urls.add(snapshot_url)
            findings.append(
                dict(
                    provider=self.name,
                    category="attack_surface",
                    title="Historic URL snapshot found",
                    description=f"Archive.org returned snapshot for {target_url} at {days} days-back",
                    entity_type="url",
                    entity_value=snapshot_url,
                    confidence=0.7,
                    tags=["archive", "historical", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"Archive.org wayback lookup for {target_url} ({days} days)",
                    raw={
                        "target": target_url,
                        "days_back": days,
                        "snapshot_url": snapshot_url,
                    },
                    confidence=0.7,
                )
            )

        return findings

    async def _query(self, target_url: str, days_back: int) -> dict:
        query = urllib.parse.urlencode(
            {"url": target_url, "timestamp": self._timestamp_for_days(days_back)}
        )
        url = f"{self.base_url}?{query}"
        payload = await self._get(
            url, label="ArchiveOrg", timeout=self._timeout_seconds
        )
        if not isinstance(payload, dict):
            raise ProviderError(
                message="Archive.org schema changed: expected object payload",
                retryable=False,
            )
        return payload

    @staticmethod
    def _timestamp_for_days(days_back: int) -> str:
        return (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y%m%d")

    @staticmethod
    def _extract_snapshot_url(payload: dict) -> str:
        archived = payload.get("archived_snapshots")
        if not isinstance(archived, dict):
            return ""
        closest = archived.get("closest")
        if not isinstance(closest, dict):
            return ""
        url = str(closest.get("url", "")).strip()
        return url

    @staticmethod
    def _normalize_days(raw_days: object) -> list[int]:
        if isinstance(raw_days, str):
            values = [v.strip() for v in raw_days.split(",") if v.strip()]
        elif isinstance(raw_days, list):
            values = [str(v).strip() for v in raw_days if str(v).strip()]
        else:
            values = ["30", "60", "90"]
        out = []
        for value in values:
            try:
                day = int(value)
            except ValueError:
                continue
            if day <= 0:
                continue
            out.append(day)
        return out or [30, 60, 90]
