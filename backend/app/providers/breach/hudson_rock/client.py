# backend/app/providers/breach/hudson_rock/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Hudson Rock Cavalier API - stealer log intelligence
import os
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class HudsonRockProvider(BaseProviderClient):
    name = "hudson_rock"
    base_url = "https://cavalier.hudsonrock.com/api/json/v2"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def get_compromised_data(
        self, *, domain: str | None = None, email: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="Hudson Rock API key is required",
                retryable=False,
            )

        headers = {"api-key": api_key, "Accept": "application/json"}
        findings: list = []
        evidence: list = []

        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"email", "domain"}:
                continue

            val = _value.strip()
            if not val:
                continue

            if _entity_type == "email":
                await self._process_email(
                    val, _entity_type, headers, findings, evidence
                )
            else:
                await self._process_domain(
                    val, _entity_type, headers, findings, evidence
                )

        return findings

    async def _process_email(
        self,
        email: str,
        _entity_type: str,
        headers: dict,
        findings: list,
        evidence: list,
    ) -> None:
        _value = email
        url = f"{self.base_url}/search-by-login?login={urllib.parse.quote(email)}"
        payload = await self._get(
            url, label="HudsonRock", headers=headers, timeout=self._timeout_seconds
        )
        if not payload:
            return

        stealers = payload.get("stealers", []) if isinstance(payload, dict) else []
        if not stealers:
            return

        dates = []
        for stealer in stealers:
            if not isinstance(stealer, dict):
                continue

            date_uploaded = str(stealer.get("date_uploaded", "unknown"))
            if date_uploaded and date_uploaded != "unknown":
                dates.append(date_uploaded)

            str(stealer.get("computer_name", "unknown"))
            operating_system = str(stealer.get("operating_system", "unknown"))
            malware_path = str(stealer.get("malware_path", ""))
            str(stealer.get("ip", "unknown"))
            credentials = stealer.get("credentials", [])
            cred_count = len(credentials) if isinstance(credentials, list) else 0

            malware_name = os.path.basename(malware_path) if malware_path else "unknown"

            description = (
                f"Stealer log hit for {email}. "
                f"Date uploaded: {date_uploaded}. "
                f"OS: {operating_system}. "
                f"Malware: {malware_name}. "
                f"Credentials found: {cred_count} (passwords not shown)."
            )

            findings.append(
                dict(
                    provider=self.name,
                    category="stealer_log_exposure",
                    title=f"Stealer log hit: {email}",
                    description=description,
                    entity_type=_entity_type,
                    entity_value=_value,
                    confidence=0.85,
                    tags=["stealer_log", "infostealer", "credential_theft"],
                )
            )

        date_range = f"{min(dates)} to {max(dates)}" if dates else "unknown"
        evidence.append(
            dict(
                source=self.name,
                description=f"Hudson Rock stealer log results for {email}",
                raw={
                    "target": email,
                    "stealer_count": len(stealers),
                    "date_range": date_range,
                },
                confidence=0.85,
            )
        )

    async def _process_domain(
        self,
        domain: str,
        _entity_type: str,
        headers: dict,
        findings: list,
        evidence: list,
    ) -> None:
        _value = domain
        url = f"{self.base_url}/search-by-domain?domain={urllib.parse.quote(domain)}"
        payload = await self._get(
            url, label="HudsonRock", headers=headers, timeout=self._timeout_seconds
        )
        if not payload:
            return

        stealers = payload.get("stealers", []) if isinstance(payload, dict) else []
        if not stealers:
            return

        for stealer in stealers:
            if not isinstance(stealer, dict):
                continue

            date_uploaded = str(stealer.get("date_uploaded", "unknown"))
            str(stealer.get("computer_name", "unknown"))
            operating_system = str(stealer.get("operating_system", "unknown"))
            credentials = stealer.get("credentials", [])
            cred_count = len(credentials) if isinstance(credentials, list) else 0

            description = (
                f"Employee/user credential exposure for domain {domain}. "
                f"Date uploaded: {date_uploaded}. "
                f"Host OS: {operating_system}. "
                f"Credentials found: {cred_count} (passwords not shown)."
            )

            findings.append(
                dict(
                    provider=self.name,
                    category="stealer_log_exposure",
                    title=f"Stealer log hit: {domain}",
                    description=description,
                    entity_type=_entity_type,
                    entity_value=_value,
                    confidence=0.85,
                    tags=["stealer_log", "infostealer", "credential_theft"],
                )
            )

        evidence.append(
            dict(
                source=self.name,
                description=f"Hudson Rock domain stealer log results for {domain}",
                raw={
                    "target": domain,
                    "stealer_count": len(stealers),
                },
                confidence=0.85,
            )
        )
