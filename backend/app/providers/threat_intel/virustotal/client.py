# backend/app/providers/threat_intel/virustotal/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity = FindingSeverity.HIGH if malicious >= 3 else FindingSeverity.MEDIUM
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_virustotal.py (MIT licensed)
# Copyright (c) Steve Micallef.
import base64
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class VirusTotalProvider(BaseProviderClient):
    name = "virustotal"
    base_url = "https://www.virustotal.com/api/v3"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_report(
        self,
        *,
        domain: str | None = None,
        ip_address: str | None = None,
        url: str | None = None,
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="VirusTotal API key is required", retryable=False
            )

        headers = {"x-apikey": api_key, "Accept": "application/json"}
        findings = []
        evidence = []

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
                url = f"{self.base_url}/domains/{value}"
            elif _entity_type == "ip_address":
                url = f"{self.base_url}/ip_addresses/{value}"
            elif _entity_type == "url":
                url_id = base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")
                url = f"{self.base_url}/urls/{url_id}"
            else:
                return findings

            data = await self._get(
                url, label="VirusTotal", headers=headers, timeout=self._timeout_seconds
            )
            attributes = data.get("data", {}).get("attributes", {})
            if not isinstance(attributes, dict):
                continue

            stats = attributes.get("last_analysis_stats", {})
            malicious = int(stats.get("malicious", 0))
            suspicious = int(stats.get("suspicious", 0))
            total = sum(int(v) for v in stats.values() if isinstance(v, int | float))

            if malicious > 0 or suspicious > 0:
                continue

                findings.append(
                    dict(
                        provider=self.name,
                        category="malware_detection",
                        title=f"VirusTotal: {malicious} malicious detections for {value}",
                        description=f"{value} flagged by {malicious} engines as malicious, {suspicious} suspicious (out of {total} total)",
                        entity_type=_entity_type,
                        entity_value=value,
                        confidence=min(1.0, (malicious / max(total, 1)) + 0.3),
                        tags=["virustotal", "malware", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"VirusTotal analysis for {value}",
                        raw={
                            "malicious": malicious,
                            "suspicious": suspicious,
                            "total": total,
                        },
                        confidence=0.85,
                    )
                )

        return findings
