# backend/app/providers/breach/snusbase/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity = FindingSeverity.HIGH if has_password else FindingSeverity.MEDIUM
# --- End migration notes ---
# Snusbase breach database API
import json
from collections import defaultdict
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class SnusbaseProvider(BaseProviderClient):
    name = "snusbase"
    base_url = "https://api.snusbase.com"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds

    async def search_breaches(
        self, *, email: str | None = None, username: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="Snusbase API key is required",
                retryable=False,
            )

        headers = {
            "Auth": api_key,
            "Content-Type": "application/json",
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

            search_type = "email" if _entity_type == "email" else "username"
            body = json.dumps({"terms": [val], "types": [search_type]})
            url = f"{self.base_url}/data/search"

            payload = await self._post(
                url,
                data=body,
                label="Snusbase",
                headers=headers,
                timeout=self._timeout_seconds,
            )
            if not payload or not isinstance(payload, dict):
                continue

            results = payload.get("results", {})
            if not results or not isinstance(results, dict):
                continue

            # Flatten all records across result buckets
            all_records: list = []
            for bucket_records in results.values():
                if isinstance(bucket_records, list):
                    all_records.extend(bucket_records)

            if not all_records:
                continue

            # Group by breach source (_table field)
            by_source: dict = defaultdict(list)
            for record in all_records:
                if isinstance(record, dict):
                    source = str(record.get("_table", "unknown_breach"))
                    by_source[source].append(record)

            any(
                bool(record.get("password") or record.get("hash"))
                for record in all_records
                if isinstance(record, dict)
            )
            has_plaintext = any(
                bool(record.get("password"))
                for record in all_records
                if isinstance(record, dict)
            )

            for source, source_records in by_source.items():
                record_has_plaintext = any(
                    bool(r.get("password")) for r in source_records
                )
                record_has_hash = any(bool(r.get("hash")) for r in source_records)
                usernames = list(
                    {r.get("username") for r in source_records if r.get("username")}
                )

                cred_detail = (
                    "plaintext credential found"
                    if record_has_plaintext
                    else (
                        "hashed credential found"
                        if record_has_hash
                        else "no credential data"
                    )
                )
                username_note = (
                    f" Associated usernames: {', '.join(usernames[:5])}."
                    if usernames
                    else ""
                )

                description = (
                    f"{val} found in breach source '{source}' with {len(source_records)} record(s). "
                    f"Credential status: {cred_detail}.{username_note}"
                )

                findings.append(
                    dict(
                        provider=self.name,
                        category="credential_exposure",
                        title=f"Snusbase breach hit: {val} in {source}",
                        description=description,
                        entity_type=_entity_type,
                        entity_value=_value,
                        confidence=0.80,
                        tags=["breach", "credential_leak", "snusbase"],
                    )
                )

            evidence.append(
                dict(
                    source=self.name,
                    description=f"Snusbase results for {val}",
                    raw={
                        "target": val,
                        "total_records": len(all_records),
                        "breach_sources": list(by_source.keys()),
                        "has_plaintext_password": has_plaintext,
                        "has_hash": any(
                            bool(r.get("hash"))
                            for r in all_records
                            if isinstance(r, dict)
                        ),
                    },
                    confidence=0.80,
                )
            )

        return findings
