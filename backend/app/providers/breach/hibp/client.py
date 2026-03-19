# backend/app/providers/breach/hibp/client.py
from __future__ import annotations

import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import ProviderError


class HibpProvider(BaseProviderClient):
    name = "haveibeenpwned"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search_breaches(
        self, *, email: str | None = None, phone_number: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="HaveIBeenPwned API key is required", retryable=False
            )

        findings = []
        _inputs: list[tuple[str, str]] = []
        if email is not None:
            _inputs.append(("email", email))
        if phone_number is not None:
            _inputs.append(("phone_number", phone_number))

        for _entity_type, _value in _inputs:
            if _entity_type not in {"email", "phone"}:
                continue
            target_value = _value.strip()
            if not target_value:
                continue
            target = urllib.parse.quote(target_value)
            url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{target}"
            headers = {
                "Accept": "application/vnd.haveibeenpwned.v3+json",
                "hibp-api-key": api_key,
            }
            payload = await self._get(
                url,
                label="HaveIBeenPwned",
                headers=headers,
                timeout=self._timeout_seconds,
            )
            if not payload:
                continue
            if not isinstance(payload, list):
                raise ProviderError(
                    message="HaveIBeenPwned schema changed: expected list payload",
                    retryable=False,
                )

            for breach in payload:
                if not isinstance(breach, dict):
                    continue
                breach_name = str(breach.get("Name", "")).strip()
                if not breach_name:
                    raise ProviderError(
                        message="HaveIBeenPwned schema changed: missing breach Name",
                        retryable=False,
                    )
                findings.append(
                    dict(
                        provider=self.name,
                        category="breach_detection",
                        title="Credential exposure in breach",
                        description=f"{_value} appears in breach dataset: {breach_name}",
                        entity_type=_entity_type,
                        entity_value=_value,
                        confidence=0.9,
                        tags=["breach", "credential_exposure", "passive"],
                    )
                )

        return findings
