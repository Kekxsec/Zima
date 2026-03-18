# backend/app/providers/breach/ghostproject/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH if password_val else FindingSeverity.MEDIUM
# --- End migration notes ---
# GhostProject - password exposure search
import re
import urllib.parse
from typing import Any

_USER_AGENT = "Zima-OSINT/1.0"
_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
_B64_RE = re.compile(r"^[A-Za-z0-9+/=]+$")


def _looks_like_hash(value: str) -> bool:
    """Return True if the value appears to be a hash rather than plaintext."""
    if not value or len(value) <= 25:
        return False
    # bcrypt / md5crypt / sha512crypt family
    if value.startswith(("$2", "$1", "$5", "$6", "$apr1")):
        return True
    # Spaces are a strong indicator of plaintext
    if " " in value:
        return False
    # Pure hex (md5=32, sha1=40, sha256=64, sha512=128, etc.)
    if _HEX_RE.match(value):
        return True
    # Base64-like without spaces
    if _B64_RE.match(value):
        return True
    return False


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class GhostProjectProvider(BaseProviderClient):
    name = "ghostproject"
    base_url = "https://ghostproject.fr/api"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def search_breaches(self, email: str) -> list[dict[str, Any]]:
        headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}
        findings: list = []
        evidence: list = []

        val = email.strip()
        if not val:
            return findings

        query = urllib.parse.quote(val)
        url = f"{self.base_url}/search?q={query}"

        payload = await self._get(
            url, label="GhostProject", headers=headers, timeout=self._timeout_seconds
        )
        if not payload:
            return findings

        # Response can be a list of records or {"found": false}
        if isinstance(payload, dict):
            if not payload.get("found", True):
                return findings
            # Unexpected dict format that isn't a "not found" response
            raise ProviderError(
                message="GhostProject schema changed: unexpected dict response",
                retryable=False,
            )

        if not isinstance(payload, list):
            raise ProviderError(
                message="GhostProject schema changed: expected list or not-found dict",
                retryable=False,
            )

        records = [r for r in payload if isinstance(r, dict)]
        if not records:
            return findings

        any_password = False
        any_plaintext = False

        for record in records:
            password_val = str(record.get("pass", ""))
            origin = str(record.get("origin", "unknown"))

            if password_val:
                any_password = True
                is_hash = _looks_like_hash(password_val)
                cred_detail = (
                    "password hash found" if is_hash else "plaintext password found"
                )
                if not is_hash:
                    any_plaintext = True
            else:
                cred_detail = "no password data in record"

            description = (
                f"{val} found in GhostProject record from source '{origin}'. "
                f"Credential status: {cred_detail} (value not shown)."
            )

            findings.append(
                dict(
                    provider=self.name,
                    category="credential_exposure",
                    title=f"GhostProject exposure: {val}",
                    description=description,
                    entity_type="email",
                    entity_value=email,
                    confidence=0.75,
                    tags=["breach", "password_exposure", "ghostproject"],
                )
            )

        evidence.append(
            dict(
                source=self.name,
                description=f"GhostProject results for {val}",
                raw={
                    "target": val,
                    "record_count": len(records),
                    "any_password_present": any_password,
                    "any_plaintext_password": any_plaintext,
                },
                confidence=0.75,
            )
        )

        return findings
