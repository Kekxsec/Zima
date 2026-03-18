# backend/app/providers/domain/robtex/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_robtex.py (MIT licensed)
# Copyright (c) Steve Micallef.
import json
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class RobtexProvider(BaseProviderClient):
    name = "robtex"
    base_url = "https://freeapi.robtex.com"

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
                url = (
                    f"{self.base_url}/pdns/forward/{urllib.parse.quote(_value.strip())}"
                )
            elif _entity_type == "ip_address":
                url = f"{self.base_url}/ipquery/{urllib.parse.quote(_value.strip())}"
            else:
                return findings

            data = self._fetch(url)
            # Forward DNS returns list of records
            records = data if isinstance(data, list) else [data]
            for rec in records:
                if not isinstance(rec, dict):
                    continue
                rrname = (
                    str(rec.get("rrname", "") or rec.get("o", "")).strip().rstrip(".")
                )
                if not rrname or rrname in seen:
                    continue
                seen.add(rrname)
                findings.append(
                    dict(
                        provider=self.name,
                        category="passive_dns",
                        title=f"Robtex passive DNS: {rrname}",
                        description=f"Robtex passive DNS record for {_value}: {rrname}",
                        entity_type="hostname",
                        entity_value=rrname,
                        confidence=0.70,
                        tags=["robtex", "passive_dns", "passive"],
                    )
                )
            if records:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Robtex passive DNS results for {_value}",
                        raw={"count": len(records)},
                        confidence=0.70,
                    )
                )

        return findings

    async def _fetch(self, url: str):
        try:
            resp = await self._get(url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="Robtex request failed", retryable=True
            ) from exc
        if resp.status_code == 429:
            raise ProviderError(message="Robtex rate limited", retryable=True)
        if resp.status_code >= 500:
            raise ProviderError(message="Robtex upstream error", retryable=True)
        if resp.status_code != 200:
            raise ProviderError(message="Robtex unexpected response", retryable=False)
        if not resp.content.strip():
            return {}
        # Robtex streams newline-delimited JSON
        results = []
        for line in resp.content.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                results.append(json.loads(line))
            except Exception:
                continue
        return results if results else {}
