# backend/app/providers/social/fullcontact/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_fullcontact.py (MIT licensed)
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class FullcontactProvider(BaseProviderClient):
    name = "fullcontact"
    base_url = "https://api.fullcontact.com/v3"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_contact_info(
        self,
        *,
        domain: str | None = None,
        email: str | None = None,
        name: str | None = None,
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="FullContact API key is required", retryable=False
            )
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        if name is not None:
            _inputs.append(("name", name))
        for _entity_type, _value in _inputs:
            val = _value.strip()
            if _entity_type == "email":
                url = f"{self.base_url}/person.enrich"
                payload = {"email": val}
            elif _entity_type == "domain":
                url = f"{self.base_url}/company.enrich"
                payload = {"domain": val}
            elif _entity_type == "human_name":
                url = f"{self.base_url}/person.enrich"
                parts = val.split()
                payload = {"fullName": val}
                if len(parts) >= 2:
                    payload["firstName"] = parts[0]
                    payload["lastName"] = parts[-1]
            else:
                return findings
            data = self._fetch_post(url, headers, payload)
            if not isinstance(data, dict):
                continue
            full_name = str(data.get("fullName", "")).strip()
            company = str(
                (data.get("employment") or [{}])[0].get("company", "")
                if isinstance(data.get("employment"), list) and data.get("employment")
                else ""
            ).strip()
            data.get("details", {}) or {}
            if full_name or company:
                desc_parts = []
                if full_name:
                    desc_parts.append(f"Name: {full_name}")
                if company:
                    desc_parts.append(f"Company: {company}")
                findings.append(
                    dict(
                        provider=self.name,
                        category="person_info",
                        title=f"FullContact: {val}",
                        description=f"FullContact enrichment for {val}: {', '.join(desc_parts)}",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.78,
                        tags=["fullcontact", "enrichment", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"FullContact data for {val}",
                        raw={"name": full_name, "company": company},
                        confidence=0.78,
                    )
                )
        return findings

    async def _fetch_post(self, url: str, headers: dict, payload: dict) -> dict:
        return await self._post(
            url,
            json_data=payload,
            label="Fullcontact",
            headers=headers,
            timeout=self._timeout_seconds,
        )
