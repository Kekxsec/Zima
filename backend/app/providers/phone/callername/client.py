# backend/app/providers/phone/callername/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_callername.py (MIT licensed)
# Copyright (c) bcoles.
import re
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class CallerNameProvider(BaseProviderClient):
    name = "callername"
    base_url = "https://callername.com"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def get_caller_info(self, phone_number: str) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        phone = phone_number.strip()
        if not phone:
            return findings
        if not phone.startswith("+1"):
            return findings
        number = self._normalize_us_number(phone)
        if not number:
            raise ProviderError(
                message=f"Unsupported input for CallerName phone lookup: {phone}",
                retryable=False,
            )
        html = await self._query(number)
        if not html:
            return findings

        location = self._extract_location(html)
        if location:
            findings.append(
                dict(
                    provider=self.name,
                    category="identity_exposure",
                    title="CallerName phone geolocation hint",
                    description=f"CallerName returned location context for {phone}",
                    entity_type="phone",
                    entity_value=phone,
                    confidence=0.6,
                    tags=["phone", "geolocation", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"CallerName location extraction for {phone}",
                    raw={"phone": phone, "location": location},
                    confidence=0.6,
                )
            )

        good_votes, bad_votes = self._extract_votes(html)
        if bad_votes > good_votes:
            findings.append(
                dict(
                    provider=self.name,
                    category="reputation",
                    title="Phone marked unsafe by CallerName votes",
                    description=f"CallerName vote ratio flagged {phone} as unsafe ({bad_votes}>{good_votes})",
                    entity_type="phone",
                    entity_value=phone,
                    confidence=0.65,
                    tags=["phone", "reputation", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"CallerName vote extraction for {phone}",
                    raw={
                        "phone": phone,
                        "good_votes": good_votes,
                        "bad_votes": bad_votes,
                    },
                    confidence=0.65,
                )
            )

        return findings

    async def _query(self, number: str) -> str:
        url = f"{self.base_url}/{number}"
        try:
            response = await self._get(url, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="CallerName request failed",
                retryable=True,
            ) from exc

        if response.status_code == 429:
            raise ProviderError(
                message="CallerName rate limited request",
                retryable=True,
            )
        if response.status_code >= 500:
            raise ProviderError(
                message="CallerName upstream unavailable",
                retryable=True,
                status_code=response.status_code,
            )
        if response.status_code == 404:
            return ""
        if response.status_code != 200:
            raise ProviderError(
                message="CallerName returned unexpected response",
                retryable=False,
                status_code=response.status_code,
            )
        return response.content or ""

    @staticmethod
    def _normalize_us_number(phone: str) -> str:
        number = "".join(ch for ch in phone if ch.isdigit())
        if number.startswith("1"):
            number = number[1:]
        if len(number) != 10:
            return ""
        return number

    @staticmethod
    def _extract_location(html: str) -> str:
        matches = re.findall(
            r'<div class="callerid"><h4>.*?</h4><p>(.+?)</p></div>',
            html,
            flags=re.MULTILINE | re.DOTALL,
        )
        if not matches:
            return ""
        location = matches[0].strip()
        if len(location) < 5 or len(location) > 100:
            return ""
        return location

    @staticmethod
    def _extract_votes(html: str) -> tuple[int, int]:
        good_match = re.findall(r">SAFE.*?>(\d+) votes?<", html)
        bad_match = re.findall(r">UNSAFE.*?>(\d+) votes?<", html)
        good = int(good_match[0]) if good_match else 0
        bad = int(bad_match[0]) if bad_match else 0
        return good, bad
