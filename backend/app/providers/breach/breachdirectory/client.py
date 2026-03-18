# backend/app/providers/breach/breachdirectory/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH if has_plaintext else FindingSeverity.MEDIUM
# --- End migration notes ---
# BreachDirectory API - breach lookup with password hash data via RapidAPI
import re
import urllib.parse
from typing import Any

_RAPIDAPI_HOST = "breachdirectory.p.rapidapi.com"
_HASH_RE = re.compile(r"^[0-9a-fA-F]{32,}$")


def _looks_like_hash(value: str) -> bool:
    """Return True if value appears to be a hash rather than plaintext."""
    if not value or len(value) < 25:
        return False
    # bcrypt / md5crypt / sha512crypt etc.
    if value.startswith(("$2", "$1", "$5", "$6", "$apr1")):
        return True
    # Pure hex string (md5, sha1, sha256, etc.)
    if _HASH_RE.match(value):
        return True
    return False


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class BreachDirectoryProvider(BaseProviderClient):
    name = "breachdirectory"
    base_url = f"https://{_RAPIDAPI_HOST}"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search_breaches(
        self, *, email: str | None = None, username: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="BreachDirectory RapidAPI key is required",
                retryable=False,
            )

        headers = {
            "X-RapidAPI-Key": api_key,
            "X-RapidAPI-Host": _RAPIDAPI_HOST,
        }
        findings: list = []
        evidence: list = []

        _inputs: list[tuple[str, str]] = []
        if email is not None:
            _inputs.append(("email", email))
        if username is not None:
            _inputs.append(("username", username))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"email", "username"}:
                continue

            val = _value.strip()
            if not val:
                continue

            term = urllib.parse.quote(val)
            url = f"{self.base_url}/?func=auto&term={term}"

            payload = await self._get(
                url,
                label="BreachDirectory",
                headers=headers,
                timeout=self._timeout_seconds,
            )
            if not payload or not isinstance(payload, dict):
                continue

            found_count = int(payload.get("found", 0))
            results = payload.get("result", [])
            if not found_count or not results:
                continue

            if not isinstance(results, list):
                raise ProviderError(
                    message="BreachDirectory schema changed: expected list in 'result'",
                    retryable=False,
                )

            any_plaintext = False
            for record in results:
                if not isinstance(record, dict):
                    continue
                password_val = str(record.get("password", ""))
                sources = record.get("sources", [])
                source_names = (
                    ", ".join(sources)
                    if isinstance(sources, list) and sources
                    else "unknown"
                )

                is_hash = _looks_like_hash(password_val)
                has_plaintext = bool(password_val) and not is_hash

                if has_plaintext:
                    any_plaintext = True

                if password_val:
                    cred_detail = (
                        "password hash exposed"
                        if is_hash
                        else "plaintext credential exposed"
                    )
                else:
                    cred_detail = "no password data in record"

                description = (
                    f"{val} found in BreachDirectory record. "
                    f"Sources: {source_names}. "
                    f"Credential status: {cred_detail}."
                )

                findings.append(
                    dict(
                        provider=self.name,
                        category="credential_exposure",
                        title=f"BreachDirectory hit: {val}",
                        description=description,
                        entity_type=_entity_type,
                        entity_value=_value,
                        confidence=0.80,
                        tags=["breach", "password_exposure", "breachdirectory"],
                    )
                )

            evidence.append(
                dict(
                    source=self.name,
                    description=f"BreachDirectory results for {val}",
                    raw={
                        "target": val,
                        "found_count": found_count,
                        "result_count": len(results),
                        "any_plaintext_password": any_plaintext,
                    },
                    confidence=0.80,
                )
            )

        return findings
