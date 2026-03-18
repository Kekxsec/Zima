# backend/app/providers/threat_intel/phishtank/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_phishtank.py (MIT licensed)
# Copyright (c) Steve Micallef.
import csv
from io import StringIO
from typing import Any
from urllib.parse import urlparse

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class PhishTankProvider(BaseProviderClient):
    name = "phishtank"
    feed_url = "https://data.phishtank.com/data/online-valid.csv"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def check_phishing(
        self, *, domain: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        try:
            response = await self._get(self.feed_url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="PhishTank request failed",
                retryable=True,
            ) from exc

        if response.status_code == 429:
            raise ProviderError(
                message="PhishTank rate limited request",
                retryable=True,
            )
        if response.status_code >= 500:
            raise ProviderError(
                message="PhishTank upstream unavailable",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code != 200:
            raise ProviderError(
                message="PhishTank returned unexpected response",
                retryable=False,
                status_code=response.status_code,
            )

        feed_hosts = self.parse_blacklist(response.content)
        findings = []
        evidence = []

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if url is not None:
            _inputs.append(("url", url))
        for _entity_type, _value in _inputs:
            host = self._entity_to_host(_entity_type, _value)
            if not host:
                continue

            matched = feed_hosts.get(host)
            if not matched:
                continue

            phish_id = matched
            findings.append(
                dict(
                    provider=self.name,
                    category="phishing_intel",
                    title="Known phishing host",
                    description=f"{host} appears in PhishTank feed (phish_id={phish_id})",
                    entity_type="hostname",
                    entity_value=host,
                    confidence=0.8,
                    tags=["phishing", "reputation", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"PhishTank feed match for {host}",
                    raw={"feed_url": self.feed_url, "host": host, "phish_id": phish_id},
                    confidence=0.8,
                )
            )

        return findings

    @staticmethod
    def _entity_to_host(entity_type: str, value: str) -> str:
        normalized = value.strip().lower()
        if entity_type in {"domain", "hostname"}:
            return normalized
        if entity_type == "url":
            parsed = urlparse(normalized)
            if parsed.hostname:
                return parsed.hostname.lower()
        return ""

    @staticmethod
    def parse_blacklist(blacklist_csv: str) -> dict[str, str]:
        if not blacklist_csv.strip():
            return {}

        mapping: dict[str, str] = {}
        csv_reader = csv.reader(StringIO(blacklist_csv))
        for row in csv_reader:
            if not row:
                continue
            if row[0].startswith("#"):
                continue
            if len(row) < 2:
                continue
            phish_id = str(row[0]).strip()
            url = str(row[1]).strip().lower()
            if not phish_id or not url:
                continue
            parsed = urlparse(url)
            host = (parsed.hostname or "").strip().lower()
            if not host or "." not in host:
                continue
            mapping[host] = phish_id
        return mapping
