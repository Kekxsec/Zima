# backend/app/providers/social/clearbit/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Clearbit was acquired by HubSpot (December 2023) and rebranded as Breeze Intelligence.
# The legacy person.clearbit.com endpoint remains accessible for migrated accounts using
# the original Clearbit API key (Basic auth). HubSpot Private App tokens (Bearer auth)
# are also accepted by the same endpoint for migrated customers.
#
# New endpoints: https://developers.hubspot.com/docs/api/enrichment
# Legacy endpoint still live: https://person.clearbit.com/v2/combined/find
import base64
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ClearbitProvider(BaseProviderClient):
    name = "clearbit"
    # HubSpot maintains the Clearbit-compat combined endpoint for migrated accounts.
    # New HubSpot enrichment endpoint: https://api.hubapi.com/enrichment/v1/...
    # We use the legacy combined endpoint which accepts both legacy Clearbit keys
    # (Basic auth) and HubSpot Private App tokens (Bearer auth).
    base_url = "https://person.clearbit.com/v2/combined/find"

    def __init__(
        self,
        api_key: str = "",
        timeout_seconds: int = 15,
        use_bearer: bool = False,
    ):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        # Set use_bearer=True when providing a HubSpot Private App token.
        # Legacy Clearbit API keys use Basic auth (use_bearer=False, the default).
        self._use_bearer = use_bearer

    async def get_contact_info(
        self, *, email: str | None = None, username: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="Clearbit/HubSpot API key is required",
                retryable=False,
            )
        use_bearer = bool(self._use_bearer)
        if use_bearer:
            headers = {
                "Accept": "application/json",
                "Authorization": f"Bearer {api_key}",
            }
        else:
            token = base64.b64encode(f"{api_key}:".encode()).decode()
            headers = {
                "Accept": "application/json",
                "Authorization": f"Basic {token}",
            }

        findings: list[dict[str, Any]] = []
        evidence: list[dict[str, Any]] = []

        _inputs: list[tuple[str, str]] = []
        if email is not None:
            _inputs.append(("email", email))
        if username is not None:
            _inputs.append(("username", username))
        for _entity_type, _value in _inputs:
            if _entity_type != "email":
                continue
            val = _value.strip().lower()
            if not val:
                continue

            url = f"{self.base_url}?{urllib.parse.urlencode({'email': val})}"
            data = self._fetch(url, headers)
            if not isinstance(data, dict):
                continue

            person = data.get("person") or {}
            company = data.get("company") or {}

            # --- Person data ---
            name_obj = person.get("name") or {}
            full_name = (
                str(name_obj.get("fullName", "")).strip()
                if isinstance(name_obj, dict)
                else ""
            )
            location = str(person.get("location", "")).strip()
            employment = person.get("employment") or {}
            employer_name = (
                str(employment.get("name", "")).strip()
                if isinstance(employment, dict)
                else ""
            )
            employer_title = (
                str(employment.get("title", "")).strip()
                if isinstance(employment, dict)
                else ""
            )
            str(person.get("bio", "")).strip()

            # Social handles
            social = person.get("twitter") or {}
            twitter_handle = (
                str(social.get("handle", "")).strip()
                if isinstance(social, dict)
                else ""
            )
            linkedin = person.get("linkedin") or {}
            linkedin_handle = (
                str(linkedin.get("handle", "")).strip()
                if isinstance(linkedin, dict)
                else ""
            )
            github = person.get("github") or {}
            github_handle = (
                str(github.get("handle", "")).strip()
                if isinstance(github, dict)
                else ""
            )

            # --- Company data ---
            company_name = str(company.get("name", "")).strip()
            company_domain = str(company.get("domain", "")).strip()
            company_type = str(company.get("type", "")).strip()
            company_employees = company.get("metrics", {}) or {}
            employee_count = (
                company_employees.get("employees")
                if isinstance(company_employees, dict)
                else None
            )

            has_person = bool(
                full_name
                or employer_name
                or twitter_handle
                or linkedin_handle
                or github_handle
            )
            has_company = bool(company_name)

            if not has_person and not has_company:
                continue

            # Build rich description
            desc_parts: list[str] = []
            if full_name:
                desc_parts.append(f"Name: {full_name}")
            if employer_name:
                role = (
                    f"{employer_title} at {employer_name}"
                    if employer_title
                    else employer_name
                )
                desc_parts.append(f"Employment: {role}")
            if location:
                desc_parts.append(f"Location: {location}")
            if twitter_handle:
                desc_parts.append(f"Twitter: @{twitter_handle}")
            if linkedin_handle:
                desc_parts.append(f"LinkedIn: {linkedin_handle}")
            if github_handle:
                desc_parts.append(f"GitHub: {github_handle}")
            if company_name:
                desc_parts.append(f"Company: {company_name}")

            tags = ["clearbit", "hubspot", "enrichment", "passive"]
            if twitter_handle:
                tags.append("twitter")
            if linkedin_handle:
                tags.append("linkedin")
            if github_handle:
                tags.append("github")

            findings.append(
                dict(
                    provider=self.name,
                    category="person_info",
                    title=f"Clearbit enrichment: {val}",
                    description="; ".join(desc_parts),
                    entity_type="email",
                    entity_value=val,
                    confidence=0.75,
                    tags=tags,
                )
            )

            # Emit social handle findings for graph building
            for handle, platform, etype in [
                (twitter_handle, "twitter", "username"),
                (github_handle, "github", "username"),
            ]:
                if handle:
                    findings.append(
                        dict(
                            provider=self.name,
                            category="alias_correlation",
                            title=f"{platform.capitalize()} handle linked to {val}",
                            description=f"Clearbit links {val} to {platform} handle @{handle}",
                            entity_type=etype,
                            entity_value=handle,
                            confidence=0.75,
                            tags=["clearbit", "alias_correlation", platform],
                        )
                    )

            raw: dict = {
                "email": val,
                "full_name": full_name,
                "employer": employer_name,
                "title": employer_title,
                "location": location,
                "twitter": twitter_handle,
                "linkedin": linkedin_handle,
                "github": github_handle,
                "company": company_name,
                "company_domain": company_domain,
                "company_type": company_type,
                "employee_count": employee_count,
            }
            evidence.append(
                dict(
                    source=self.name,
                    description=f"Clearbit/HubSpot enrichment for {val}",
                    raw={k: v for k, v in raw.items() if v},
                    confidence=0.75,
                )
            )

        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        try:
            resp = await self._get(url, headers=headers, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="Clearbit request failed",
                retryable=True,
            ) from exc
        if resp.status_code in {401, 402}:
            raise ProviderError(
                message="Clearbit/HubSpot rejected credentials — check API key and subscription status",
                retryable=False,
            )
        # 404 = person not found (not an error)
        if resp.status_code == 404:
            return {}
        # 422 = validation error (bad email format etc.)
        if resp.status_code == 422:
            return {}
        self._check_status_errors(resp, "Clearbit")
        return self._parse_json(resp, "Clearbit")
