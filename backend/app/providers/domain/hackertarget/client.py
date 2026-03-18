# backend/app/providers/domain/hackertarget/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_hackertarget.py (MIT licensed)
# Copyright (c) Steve Micallef.
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class HackerTargetProvider(BaseProviderClient):
    name = "hackertarget"
    base_url = "https://api.hackertarget.com"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def enumerate_subdomains(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen: set[str] = set()

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type == "domain":
                target = _value.strip().lower().strip(".")
                endpoint = f"{self.base_url}/hostsearch/?q={urllib.parse.quote(target)}"
                result_type = "subdomain"
            elif _entity_type == "ip_address":
                target = _value.strip()
                endpoint = (
                    f"{self.base_url}/reverseiplookup/?q={urllib.parse.quote(target)}"
                )
                result_type = "reverse_ip"
            else:
                return findings

            data = self._fetch(endpoint)
            if not data:
                continue

            for line in data.splitlines():
                line = line.strip()
                if not line or "error" in line.lower() or line in seen:
                    continue
                # hostsearch returns "hostname,ip" lines; reverseip returns hostnames
                value = line.split(",")[0].strip()
                if not value or value in seen:
                    continue
                seen.add(value)
                findings.append(
                    dict(
                        provider=self.name,
                        category="dns_discovery"
                        if result_type == "subdomain"
                        else "reverse_ip",
                        title=f"HackerTarget {result_type}: {value}",
                        description=f"{result_type.replace('_', ' ').title()} discovered via HackerTarget: {value}",
                        entity_type="hostname",
                        entity_value=value,
                        confidence=0.70,
                        tags=["hackertarget", result_type, "passive"],
                    )
                )
            if data.strip():
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"HackerTarget {result_type} results for {target}",
                        raw={
                            "target": target,
                            "type": result_type,
                            "lines": len(data.splitlines()),
                        },
                        confidence=0.70,
                    )
                )

        return findings

    async def _fetch(self, url: str) -> str:
        try:
            resp = await self._get(url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="HackerTarget request failed", retryable=True
            ) from exc
        if resp.status_code == 429:
            raise ProviderError(message="HackerTarget rate limited", retryable=True)
        if resp.status_code >= 500:
            raise ProviderError(message="HackerTarget upstream error", retryable=True)
        if resp.status_code != 200:
            raise ProviderError(
                message="HackerTarget unexpected response", retryable=False
            )
        return resp.content or ""
