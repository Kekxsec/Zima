# backend/app/providers/content_analysis/countryname/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_countryname.py (MIT licensed)
# Copyright (c) Steve Micallef.
import re
from typing import Any

# ISO 3166-1 country names (subset of common ones for pattern matching)
_COUNTRIES = [
    "Afghanistan",
    "Albania",
    "Algeria",
    "Argentina",
    "Australia",
    "Austria",
    "Azerbaijan",
    "Bahrain",
    "Bangladesh",
    "Belarus",
    "Belgium",
    "Bolivia",
    "Brazil",
    "Bulgaria",
    "Cambodia",
    "Canada",
    "Chile",
    "China",
    "Colombia",
    "Croatia",
    "Cuba",
    "Czech Republic",
    "Denmark",
    "Ecuador",
    "Egypt",
    "Ethiopia",
    "Finland",
    "France",
    "Germany",
    "Ghana",
    "Greece",
    "Guatemala",
    "Honduras",
    "Hong Kong",
    "Hungary",
    "India",
    "Indonesia",
    "Iran",
    "Iraq",
    "Ireland",
    "Israel",
    "Italy",
    "Japan",
    "Jordan",
    "Kazakhstan",
    "Kenya",
    "Kuwait",
    "Lebanon",
    "Libya",
    "Lithuania",
    "Malaysia",
    "Mexico",
    "Morocco",
    "Myanmar",
    "Nepal",
    "Netherlands",
    "New Zealand",
    "Nigeria",
    "North Korea",
    "Norway",
    "Oman",
    "Pakistan",
    "Palestine",
    "Panama",
    "Paraguay",
    "Peru",
    "Philippines",
    "Poland",
    "Portugal",
    "Qatar",
    "Romania",
    "Russia",
    "Saudi Arabia",
    "Serbia",
    "Singapore",
    "Slovakia",
    "South Africa",
    "South Korea",
    "Spain",
    "Sri Lanka",
    "Sudan",
    "Sweden",
    "Switzerland",
    "Syria",
    "Taiwan",
    "Thailand",
    "Tunisia",
    "Turkey",
    "Ukraine",
    "United Arab Emirates",
    "United Kingdom",
    "United States",
    "Uruguay",
    "Uzbekistan",
    "Venezuela",
    "Vietnam",
    "Yemen",
    "Zimbabwe",
]

_PATTERN = re.compile(
    r"\b("
    + "|".join(re.escape(c) for c in sorted(_COUNTRIES, key=len, reverse=True))
    + r")\b",
    re.IGNORECASE,
)


from backend.app.providers.base.client import BaseProviderClient


class CountrynameProvider(BaseProviderClient):
    name = "countryname"

    async def detect_countries(
        self, *, content: str | None = None, address: str | None = None
    ) -> list[dict[str, Any]]:
        findings = []
        evidence = []
        seen: set[str] = set()

        _inputs: list[tuple[str, str]] = []
        if content is not None:
            _inputs.append(("content", content))
        if address is not None:
            _inputs.append(("address", address))
        for _entity_type, _value in _inputs:
            if _entity_type not in {
                "web_content",
                "binary_content",
                "physical_address",
            }:
                return findings
            if not _value:
                continue
            for match in _PATTERN.findall(_value):
                country = match.strip().title()
                if country in seen:
                    continue
                seen.add(country)
                findings.append(
                    dict(
                        provider=self.name,
                        category="geolocation",
                        title=f"Country name found: {country}",
                        description=f"Country name '{country}' identified in content",
                        entity_type="country_name",
                        entity_value=country,
                        confidence=0.55,
                        tags=[
                            "content_analysis",
                            "countryname",
                            "geolocation",
                            "passive",
                        ],
                    )
                )
        if findings:
            evidence.append(
                dict(
                    source=self.name,
                    description="Country names detected in content",
                    raw={"countries": list(seen)},
                    confidence=0.55,
                )
            )

        return findings
