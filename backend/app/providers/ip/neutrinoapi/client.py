# backend/app/providers/ip/neutrinoapi/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_neutrinoapi.py (MIT licensed)
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class NeutrinoApiProvider(BaseProviderClient):
    name = "neutrinoapi"
    base_url = "https://neutrinoapi.net"

    def __init__(self, user_id: str = "", api_key: str = "", timeout_seconds: int = 15):
        self._user_id = user_id
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_host_info(
        self,
        *,
        email: str | None = None,
        ip_address: str | None = None,
        phone_number: str | None = None,
    ) -> list[dict[str, Any]]:
        user_id = str(self._user_id).strip()
        api_key = str(self._api_key).strip()
        if not user_id or not api_key:
            raise ProviderError(
                message="Neutrino API user ID and API key are required", retryable=False
            )
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if email is not None:
            _inputs.append(("email", email))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        if phone_number is not None:
            _inputs.append(("phone_number", phone_number))
        for _entity_type, _value in _inputs:
            val = _value.strip()
            if _entity_type == "ip_address":
                endpoint = "/ip-blocklist"
                payload = {"user-id": user_id, "api-key": api_key, "ip": val}
                data = self._fetch_post(f"{self.base_url}{endpoint}", payload)
                is_listed = (
                    data.get("is-listed", False) if isinstance(data, dict) else False
                )
                if is_listed:
                    lists = data.get("blocklists", []) or []
                    findings.append(
                        dict(
                            provider=self.name,
                            category="blocklist",
                            title=f"NeutrinoAPI blocklist: {val}",
                            description=f"IP {val} found in {len(lists)} blocklist(s) via NeutrinoAPI",
                            entity_type="ip_address",
                            entity_value=val,
                            confidence=0.82,
                            tags=["neutrinoapi", "blocklist", "passive"],
                        )
                    )
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"NeutrinoAPI blocklist for {val}",
                            raw={"lists": lists[:5]},
                            confidence=0.82,
                        )
                    )
            elif _entity_type == "phone":
                endpoint = "/phone-validate"
                payload = {"user-id": user_id, "api-key": api_key, "number": val}
                data = self._fetch_post(f"{self.base_url}{endpoint}", payload)
                valid = data.get("valid", False) if isinstance(data, dict) else False
                if valid:
                    country = str(data.get("country", "")).strip()
                    number_type = str(data.get("type", "")).strip()
                    findings.append(
                        dict(
                            provider=self.name,
                            category="phone_number",
                            title=f"NeutrinoAPI phone: {val}",
                            description=f"Phone {val} is valid: {number_type} in {country}",
                            entity_type="phone",
                            entity_value=val,
                            confidence=0.85,
                            tags=["neutrinoapi", "phone", "passive"],
                        )
                    )
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"NeutrinoAPI phone validation for {val}",
                            raw={"country": country, "type": number_type},
                            confidence=0.85,
                        )
                    )
        return findings

    async def _fetch_post(self, url: str, payload: dict) -> dict:
        return await self._post(
            url, json_data=payload, label="NeutrinoApi", timeout=self._timeout_seconds
        )
