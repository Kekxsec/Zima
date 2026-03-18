# backend/app/providers/reputation/botscout/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_botscout.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class BotScoutProvider(BaseProviderClient):
    name = "botscout"
    base_url = "https://botscout.com/test/"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_reputation(
        self, *, email: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        findings = []
        evidence = []
        _inputs: list[tuple[str, str]] = []
        if email is not None:
            _inputs.append(("email", email))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            target = _value.strip()
            if not target:
                continue

            if _entity_type == "ip_address":
                if not self._is_valid_ip(target):
                    raise ProviderError(
                        message=f"Unsupported input for BotScout IP query: {target}",
                        retryable=False,
                    )
                response_text = await self._query_ip(target, api_key)
                if not response_text.startswith("Y|"):
                    continue
                findings.append(
                    dict(
                        provider=self.name,
                        category="reputation",
                        title="IP reported by BotScout",
                        description=f"{target} matched BotScout bot/spam indicators ({response_text})",
                        entity_type="ip_address",
                        entity_value=target,
                        confidence=0.7,
                        tags=["reputation", "botscout", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"BotScout IP query response for {target}",
                        raw={"target": target, "response": response_text},
                        confidence=0.7,
                    )
                )

            if _entity_type == "email":
                if "@" not in target or target.startswith("@") or target.endswith("@"):
                    raise ProviderError(
                        message=f"Unsupported input for BotScout email query: {target}",
                        retryable=False,
                    )
                response_text = await self._query_email(target, api_key)
                if not response_text.startswith("Y|"):
                    continue
                findings.append(
                    dict(
                        provider=self.name,
                        category="reputation",
                        title="Email reported by BotScout",
                        description=f"{target} matched BotScout bot/spam indicators ({response_text})",
                        entity_type="email",
                        entity_value=target,
                        confidence=0.7,
                        tags=["reputation", "botscout", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"BotScout email query response for {target}",
                        raw={"target": target, "response": response_text},
                        confidence=0.7,
                    )
                )

        return findings

    async def _query_ip(self, ip_value: str, api_key: str) -> str:
        params = {"ip": ip_value}
        if api_key:
            params["key"] = api_key
        return await self._query(params)

    async def _query_email(self, email_value: str, api_key: str) -> str:
        params = {"mail": email_value}
        if api_key:
            params["key"] = api_key
        return await self._query(params)

    async def _query(self, params: dict[str, str]) -> str:
        query = urllib.parse.urlencode(params)
        url = f"{self.base_url}?{query}"
        try:
            response = await self._get(url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="BotScout request failed",
                retryable=True,
            ) from exc

        if response.status_code in {401, 403}:
            raise ProviderError(
                message="BotScout rejected API key",
                retryable=False,
                status_code=response.status_code,
            )
        if response.status_code == 429:
            raise ProviderError(
                message="BotScout rate limited request",
                retryable=True,
            )
        if response.status_code >= 500:
            raise ProviderError(
                message="BotScout upstream unavailable",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code != 200:
            raise ProviderError(
                message="BotScout returned unexpected response",
                retryable=False,
                status_code=response.status_code,
            )

        content = (response.content or "").strip()
        if not content:
            raise ProviderError(
                message="BotScout returned empty response body",
                retryable=False,
            )
        if content.startswith("!"):
            raise ProviderError(
                message=f"BotScout returned error response: {content}",
                retryable=False,
            )
        if not (content.startswith("Y|") or content.startswith("N|")):
            raise ProviderError(
                message="BotScout schema changed: expected Y| or N| response",
                retryable=False,
            )
        return content

    @staticmethod
    def _is_valid_ip(value: str) -> bool:
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False
