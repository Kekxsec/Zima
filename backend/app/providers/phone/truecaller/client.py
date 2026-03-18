# backend/app/providers/phone/truecaller/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity = FindingSeverity.MEDIUM if linked_emails else FindingSeverity.LOW
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---
import re
import urllib.parse
from typing import Any

# Digits-only pattern used to strip non-numeric chars before E.164 normalisation
_NON_DIGIT = re.compile(r"[^\d+]")


def _normalize_e164(phone: str) -> str:
    """Best-effort normalisation to E.164 format.

    If the value already starts with '+' it is returned as-is (digits only after
    the +).  Otherwise a leading '+' is prepended so the TrueCaller API receives
    a valid international number.
    """
    phone = phone.strip()
    if phone.startswith("+"):
        digits = re.sub(r"\D", "", phone[1:])
        return f"+{digits}"
    digits = re.sub(r"\D", "", phone)
    return f"+{digits}"


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class TruecallerProvider(BaseProviderClient):
    """TrueCaller - phone number reverse lookup."""

    name = "truecaller"
    base_url = "https://search5-noneu.truecaller.com/v2"

    def __init__(self, auth_token: str = "", timeout_seconds: int = 15):
        self._auth_token = auth_token
        self._timeout_seconds = timeout_seconds

    async def lookup_phone(self, phone_number: str) -> list[dict[str, Any]]:
        auth_token = str(self._auth_token).strip()
        if not auth_token:
            raise ProviderError(
                message="TrueCaller auth token is required",
                retryable=False,
            )

        findings: list = []
        evidence: list = []

        phone_raw = phone_number.strip()
        phone_e164 = _normalize_e164(phone_raw)

        params = urllib.parse.urlencode(
            {"q": phone_e164, "type": 4, "encoding": "json"}
        )
        url = f"{self.base_url}/search?{params}"

        data = await self._get(
            url,
            label="TrueCaller",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=self._timeout_seconds,
        )

        records = data.get("data") or []
        if not isinstance(records, list) or not records:
            return findings

        for record in records:
            name = str(record.get("name", "")).strip()
            score = float(record.get("score", 0.0))

            phones_list = record.get("phones") or []
            carrier = ""
            number_type = ""
            national_fmt = ""
            if phones_list and isinstance(phones_list[0], dict):
                ph = phones_list[0]
                carrier = str(ph.get("carrier", "")).strip()
                number_type = str(ph.get("numberType", "")).strip()
                national_fmt = str(ph.get("nationalFormat", "")).strip()

            addresses = record.get("addresses") or []
            city = ""
            country_code = ""
            timezone = ""
            if addresses and isinstance(addresses[0], dict):
                addr = addresses[0]
                city = str(addr.get("city", "")).strip()
                country_code = str(addr.get("countryCode", "")).strip()
                timezone = str(addr.get("timeZone", "")).strip()

            internet_addresses = record.get("internetAddresses") or []
            linked_emails = [
                str(ia.get("id", "")).strip()
                for ia in internet_addresses
                if isinstance(ia, dict)
                and str(ia.get("service", "")).lower() == "email"
                and ia.get("id")
            ]

            # Build description
            desc_parts = [f"TrueCaller lookup for {phone_e164}."]
            if name:
                desc_parts.append(f"Name: {name}.")
            if carrier:
                desc_parts.append(f"Carrier: {carrier}.")
            if number_type:
                desc_parts.append(f"Type: {number_type}.")
            if city or country_code:
                location = ", ".join(p for p in [city, country_code] if p)
                desc_parts.append(f"Location: {location}.")
            if timezone:
                desc_parts.append(f"Timezone: {timezone}.")
            if linked_emails:
                desc_parts.append(f"Linked email(s): {', '.join(linked_emails)}.")

            findings.append(
                dict(
                    provider=self.name,
                    category="phone_exposure",
                    title=f"TrueCaller: {phone_e164}",
                    description=" ".join(desc_parts),
                    entity_type="phone",
                    entity_value=phone_e164,
                    confidence=0.70,
                    tags=["truecaller", "phone_lookup", "passive"],
                )
            )

            # Separate findings for any linked email addresses
            for linked_email in linked_emails:
                findings.append(
                    dict(
                        provider=self.name,
                        category="phone_exposure",
                        title=f"TrueCaller: phone {phone_e164} linked to email {linked_email}",
                        description=(
                            f"TrueCaller profile for {phone_e164} contains a linked email "
                            f"address: {linked_email}."
                        ),
                        entity_type="phone",
                        entity_value=phone_e164,
                        confidence=0.70,
                        tags=["truecaller", "phone_lookup", "passive", "linked_email"],
                    )
                )

            evidence.append(
                dict(
                    source=self.name,
                    description=f"TrueCaller profile data for {phone_e164}",
                    raw={
                        "name": name,
                        "score": score,
                        "carrier": carrier,
                        "number_type": number_type,
                        "national_format": national_fmt,
                        "city": city,
                        "country_code": country_code,
                        "timezone": timezone,
                        "linked_emails": linked_emails,
                    },
                    confidence=0.70,
                )
            )

        return findings
