# backend/app/providers/breach/illicit_services/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity = FindingSeverity.HIGH if has_password else FindingSeverity.MEDIUM
# --- End migration notes ---
# Illicit.Services - free breach record search
import urllib.parse
from collections import defaultdict
from typing import Any

_USER_AGENT = "Zima-OSINT/1.0"


from backend.app.providers.base.client import BaseProviderClient


class IllicitServicesProvider(BaseProviderClient):
    name = "illicit_services"
    base_url = "https://search.illicit.services"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def search_breaches(
        self, *, email: str | None = None, username: str | None = None
    ) -> list[dict[str, Any]]:
        headers = {"User-Agent": _USER_AGENT, "Accept": "application/json"}
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

            query = urllib.parse.quote(val)
            url = f"{self.base_url}/records/search?q={query}"

            payload = await self._get(
                url,
                label="IllicitServices",
                headers=headers,
                timeout=self._timeout_seconds,
            )
            if not payload or not isinstance(payload, dict):
                continue

            results = payload.get("results", [])
            total = int(payload.get("total", 0))

            if not results or not isinstance(results, list):
                continue

            # Group by breach source
            by_source: dict = defaultdict(list)
            for record in results:
                if isinstance(record, dict):
                    source = str(record.get("source", "unknown"))
                    by_source[source].append(record)

            for source, source_records in by_source.items():
                has_password = any(bool(r.get("password")) for r in source_records)

                cred_note = (
                    " Credential data present (passwords not shown)."
                    if has_password
                    else ""
                )
                description = f"{val} found in breach source '{source}' with {len(source_records)} record(s).{cred_note}"

                findings.append(
                    dict(
                        provider=self.name,
                        category="credential_exposure",
                        title=f"Illicit.Services breach hit: {val} in {source}",
                        description=description,
                        entity_type=_entity_type,
                        entity_value=_value,
                        confidence=0.75,
                        tags=["breach", "free_source", "illicit_services"],
                    )
                )

            evidence.append(
                dict(
                    source=self.name,
                    description=f"Illicit.Services results for {val}",
                    raw={
                        "target": val,
                        "total": total,
                        "result_count": len(results),
                        "breach_sources": list(by_source.keys()),
                    },
                    confidence=0.75,
                )
            )

        return findings
