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

    def __init__(self, api_key: str = "", timeout_seconds: int = 15) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self._api_key = api_key

    async def validate_email(self, email: str) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="Epieos API key is required",
                retryable=False,
            )

        findings: list[dict[str, Any]] = []

        email = email.strip()
        params = urllib.parse.urlencode({"email": email, "format": "json"})
        url = f"{self.base_url}/email?{params}"

        # _get() handles: 404 → returns {}, 429 → raises ProviderRateLimitError,
        # 401/403 → raises ProviderAuthError, 5xx → raises ProviderUpstreamError.
        # 402 (quota exceeded) returns an error JSON body without google/apple keys
        # so no findings will be emitted — acceptable behaviour.
        data = await self._get(
            url,
            headers={"EPIEOS-TOKEN": api_key},
            timeout=self._timeout_seconds,
        )

        if not data:
            return findings

        google = data.get("google") or {}
        apple = data.get("apple") or {}
        services = data.get("services") or []

        service_tags = [
            "google_account",
            "apple_id",
            "account_enumeration",
            "passive",
        ] + [str(s) for s in services if isinstance(s, str)]

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
                    tags=service_tags,
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
                )
            )

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
                    tags=service_tags,
                    raw={
                        "apple_id": apple.get("id"),
                        "email_verified": apple.get("email_verified"),
                    },
                )
            )

        return findings
