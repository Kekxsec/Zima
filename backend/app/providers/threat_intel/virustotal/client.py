# backend/app/providers/threat_intel/virustotal/client.py
"""
VirusTotalProvider — URL, domain, and IP reputation via the VirusTotal v3 API.

Adapted from SpiderFoot module: modules/sfp_virustotal.py (MIT licensed)
Copyright (c) Steve Micallef.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import ProviderError


@dataclass(frozen=True)
class UrlScanResult:
    """Result of a VirusTotal URL reputation lookup."""

    url: str
    is_malicious: bool
    malicious_count: int
    suspicious_count: int
    total_engines: int
    # Link to the VT report page — useful as evidence in signals
    permalink: str | None = None

    @property
    def verdict(self) -> str:
        if self.is_malicious:
            return "malicious"
        if self.suspicious_count >= 3:
            return "suspicious"
        return "clean"


# Thresholds for flagging a URL as malicious
_MALICIOUS_THRESHOLD = 1  # any single engine detection = flag
_SUSPICIOUS_THRESHOLD = 3  # 3+ suspicious engines = flag


class VirusTotalProvider(BaseProviderClient):
    name = "virustotal"
    base_url = "https://www.virustotal.com/api/v3"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def scan_url(self, url: str) -> UrlScanResult:
        """
        Check a URL against VirusTotal's existing analysis database.

        Uses GET /urls/{id} — no scan submission, no quota for new analyses.
        Degrades gracefully:
          - 404: URL not in VT database → returns is_malicious=False
          - API key missing: raises ProviderError(retryable=False)
          - 429 / network error: raises ProviderError(retryable=True)

        Malicious threshold: any engine flags it OR 3+ suspicious engines.
        """
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="VirusTotal API key is required", retryable=False
            )

        # VT URL ID = base64url(url) without padding
        url_id = base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
        endpoint = f"{self.base_url}/urls/{url_id}"
        headers = {"x-apikey": api_key, "Accept": "application/json"}

        try:
            data = await self._get(
                endpoint,
                label="virustotal",
                headers=headers,
                timeout=self._timeout_seconds,
            )
        except ProviderError as exc:
            # 404 → URL not in database → fail open (not malicious)
            if "404" in str(exc):
                return UrlScanResult(
                    url=url,
                    is_malicious=False,
                    malicious_count=0,
                    suspicious_count=0,
                    total_engines=0,
                )
            raise

        attributes = data.get("data", {}).get("attributes", {})
        if not isinstance(attributes, dict):
            return UrlScanResult(
                url=url,
                is_malicious=False,
                malicious_count=0,
                suspicious_count=0,
                total_engines=0,
            )

        stats = attributes.get("last_analysis_stats", {})
        malicious = int(stats.get("malicious", 0))
        suspicious = int(stats.get("suspicious", 0))
        total = sum(int(v) for v in stats.values() if isinstance(v, int | float))

        is_malicious = (
            malicious >= _MALICIOUS_THRESHOLD or suspicious >= _SUSPICIOUS_THRESHOLD
        )

        permalink: str | None = None
        links = data.get("data", {}).get("links", {})
        if isinstance(links, dict):
            permalink = links.get("self")

        return UrlScanResult(
            url=url,
            is_malicious=is_malicious,
            malicious_count=malicious,
            suspicious_count=suspicious,
            total_engines=total,
            permalink=permalink,
        )

    async def get_report(
        self,
        *,
        domain: str | None = None,
        ip_address: str | None = None,
        url: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Generic multi-target report lookup. Returns a list of finding dicts
        for any target with malicious or suspicious detections.
        """
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="VirusTotal API key is required", retryable=False
            )

        headers = {"x-apikey": api_key, "Accept": "application/json"}
        findings: list[dict[str, Any]] = []

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        if url is not None:
            _inputs.append(("url", url))

        for _entity_type, _value in _inputs:
            value = _value.strip()
            if _entity_type == "domain":
                endpoint = f"{self.base_url}/domains/{value}"
            elif _entity_type == "ip_address":
                endpoint = f"{self.base_url}/ip_addresses/{value}"
            elif _entity_type == "url":
                url_id = base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")
                endpoint = f"{self.base_url}/urls/{url_id}"
            else:
                continue

            try:
                data = await self._get(
                    endpoint,
                    label="virustotal",
                    headers=headers,
                    timeout=self._timeout_seconds,
                )
            except ProviderError:
                continue

            attributes = data.get("data", {}).get("attributes", {})
            if not isinstance(attributes, dict):
                continue

            stats = attributes.get("last_analysis_stats", {})
            malicious = int(stats.get("malicious", 0))
            suspicious = int(stats.get("suspicious", 0))
            total = sum(int(v) for v in stats.values() if isinstance(v, int | float))

            if malicious > 0 or suspicious > 0:
                findings.append(
                    dict(
                        provider=self.name,
                        category="malware_detection",
                        title=f"VirusTotal: {malicious} malicious detections for {value}",
                        description=(
                            f"{value} flagged by {malicious} engines as malicious, "
                            f"{suspicious} suspicious (out of {total} total)"
                        ),
                        entity_type=_entity_type,
                        entity_value=value,
                        confidence=min(1.0, (malicious / max(total, 1)) + 0.3),
                        tags=["virustotal", "malware", "passive"],
                        malicious_count=malicious,
                        suspicious_count=suspicious,
                    )
                )

        return findings
