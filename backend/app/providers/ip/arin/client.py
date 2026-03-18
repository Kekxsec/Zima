# backend/app/providers/ip/arin/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_arin.py (MIT licensed)
# Copyright (c) Steve Micallef.
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ARINProvider(BaseProviderClient):
    name = "arin"
    base_url = "https://whois.arin.net/rest"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def get_network_info(
        self, *, domain: str | None = None, name: str | None = None
    ) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen_names = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if name is not None:
            _inputs.append(("name", name))
        for _entity_type, _value in _inputs:
            value = _value.strip()
            if not value:
                continue

            if _entity_type == "domain":
                payload = await self._query_domain(value)
            elif _entity_type == "human_name":
                payload = await self._query_name(value)
            else:
                continue

            poc_refs = self._extract_poc_refs(payload)
            for poc in poc_refs:
                display_name = self._normalize_name(str(poc.get("@name", "")).strip())
                if not display_name:
                    continue
                if display_name in seen_names:
                    continue
                seen_names.add(display_name)
                findings.append(
                    dict(
                        provider=self.name,
                        category="identity_exposure",
                        title="ARIN contact record",
                        description=f"ARIN lookup discovered contact '{display_name}' for {value}",
                        entity_type="human_name",
                        entity_value=display_name,
                        confidence=0.7,
                        tags=["whois", "arin", "passive"],
                    )
                )

            if poc_refs:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"ARIN lookup response for {value}",
                        raw={"query": value, "poc_count": len(poc_refs)},
                        confidence=0.7,
                    )
                )

        return findings

    async def _query_domain(self, domain: str) -> dict:
        resource = f"pocs;domain=@{urllib.parse.quote(domain)}"
        return await self._get_json(f"{self.base_url}/{resource}")

    async def _query_name(self, human_name: str) -> dict:
        parts = human_name.split()
        if len(parts) < 2:
            raise ProviderError(
                message=f"Unsupported ARIN human name input: {human_name}",
                retryable=False,
            )
        first = parts[0].rstrip(",")
        last = " ".join(parts[1:])
        resource = (
            f"pocs;first={urllib.parse.quote(first)};last={urllib.parse.quote(last)}"
        )
        return await self._get_json(f"{self.base_url}/{resource}")

    async def _get_json(self, url: str) -> dict:
        headers = {"Accept": "application/json"}
        payload = await self._get(
            url, label="ARIN", headers=headers, timeout=self._timeout_seconds
        )
        if not isinstance(payload, dict):
            raise ProviderError(
                message="ARIN schema changed: expected object payload",
                retryable=False,
            )
        return payload

    @staticmethod
    def _extract_poc_refs(payload: dict) -> list[dict]:
        pocs = payload.get("pocs")
        if not isinstance(pocs, dict):
            return []
        refs = pocs.get("pocRef")
        if isinstance(refs, dict):
            return [refs]
        if isinstance(refs, list):
            return [ref for ref in refs if isinstance(ref, dict)]
        return []

    @staticmethod
    def _normalize_name(name: str) -> str:
        if not name:
            return ""
        if ", " in name:
            left, right = name.split(", ", 1)
            return f"{right} {left}".strip()
        return name
