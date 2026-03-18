# backend/app/providers/social/epieos/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM
# STRIPPED: severity=FindingSeverity.LOW
# --- End migration notes ---
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class EpieosProvider(BaseProviderClient):
    """Epieos - Google & Apple account OSINT from email address."""

    name = "epieos"
    base_url = "https://epieos.com/api"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def validate_email(self, email: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="Epieos API key is required",
                retryable=False,
            )

        findings: list = []
        evidence: list = []

        email = email.strip()
        params = urllib.parse.urlencode({"email": email, "format": "json"})
        url = f"{self.base_url}/email?{params}"

        resp = await self._get(
            url,
            headers={"EPIEOS-TOKEN": api_key},
            timeout=self._timeout_seconds,
        )

        if resp.status_code == 402:
            raise ProviderError(
                message="Epieos payment required — quota exceeded or subscription inactive",
                retryable=False,
            )
        if resp.status_code == 429:
            raise ProviderError(
                message="Epieos rate limited",
                retryable=True,
            )

        self._check_status_errors(resp, "Epieos")

        if resp.status_code == 404 or not resp.content.strip():
            return findings

        data = self._parse_json(resp, "Epieos")

        google = data.get("google") or {}
        apple = data.get("apple") or {}
        services = data.get("services") or []

        service_tags = [
            "google_account",
            "apple_id",
            "account_enumeration",
            "passive",
        ] + [str(s) for s in services if isinstance(s, str)]

        # Google account finding
        if google and google.get("id"):
            name = str(google.get("name", "")).strip()
            last_activity = str(google.get("lastActivity", "")).strip()
            maps_reviews = google.get("mapsReviews", 0)
            photos_public = google.get("photosPublic", 0)

            desc_parts = [f"Google account confirmed for {email}."]
            if name:
                desc_parts.append(f"Name: {name}.")
            if last_activity:
                desc_parts.append(f"Last activity: {last_activity}.")
            if maps_reviews:
                desc_parts.append(f"Maps reviews: {maps_reviews}.")
            if photos_public:
                desc_parts.append(f"Public photos: {photos_public}.")

            findings.append(
                dict(
                    provider=self.name,
                    category="account_enumeration_risk",
                    title=f"Google account confirmed: {email}",
                    description=" ".join(desc_parts),
                    entity_type="email",
                    entity_value=email,
                    confidence=0.85,
                    tags=service_tags,
                )
            )

            evidence.append(
                dict(
                    source=self.name,
                    description=f"Epieos Google account data for {email}",
                    raw={
                        "google_id": google.get("id"),
                        "name": google.get("name"),
                        "lastActivity": google.get("lastActivity"),
                        "mapsReviews": google.get("mapsReviews"),
                        "calendarEvents": google.get("calendarEvents"),
                        "photosPublic": google.get("photosPublic"),
                        "youtubeChannel": google.get("youtubeChannel"),
                        "hangoutsLastActivity": google.get("hangoutsLastActivity"),
                    },
                    confidence=0.85,
                )
            )

        # Apple ID finding
        if apple and apple.get("id"):
            findings.append(
                dict(
                    provider=self.name,
                    category="account_enumeration_risk",
                    title=f"Apple ID confirmed: {email}",
                    description=(
                        f"Apple ID account confirmed for {email}. "
                        f"Email verified: {apple.get('email_verified', False)}."
                    ),
                    entity_type="email",
                    entity_value=email,
                    confidence=0.75,
                    tags=service_tags,
                )
            )

            evidence.append(
                dict(
                    source=self.name,
                    description=f"Epieos Apple ID data for {email}",
                    raw={
                        "apple_id": apple.get("id"),
                        "email_verified": apple.get("email_verified"),
                    },
                    confidence=0.75,
                )
            )

        return findings
