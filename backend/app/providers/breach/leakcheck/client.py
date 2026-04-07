# backend/app/providers/breach/leakcheck/client.py
from __future__ import annotations

# LeakCheck.io - email and username breach lookup
import urllib.parse
from typing import Any

from pydantic import SecretStr

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class LeakCheckProvider(BaseProviderClient):
    name = "leakcheck"
    public_base_url = "https://leakcheck.io/api/public"
    v2_base_url = "https://leakcheck.io/api/v2/query"

    def __init__(self, api_key: str = "", timeout_seconds: int = 15) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self._api_key: SecretStr = SecretStr(api_key)

    async def check_leaks(
        self, *, email: str | None = None, username: str | None = None
    ) -> list[dict[str, Any]]:
        api_key = self._api_key.get_secret_value().strip()
        findings: list[dict[str, Any]] = []

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

            encoded = urllib.parse.quote(val)

            if api_key:
                url = f"{self.v2_base_url}/{encoded}"
                headers: dict[str, str] = {
                    "X-API-Key": api_key,
                    "Accept": "application/json",
                }
            else:
                url = f"{self.public_base_url}?check={encoded}"
                headers = {"Accept": "application/json"}

            payload = await self._get(
                url, label="LeakCheck", headers=headers, timeout=self._timeout_seconds
            )
            if not payload or not isinstance(payload, dict):
                continue

            success = payload.get("success", False)
            if not success:
                continue

            found_count = int(payload.get("found") or 0)
            sources = payload.get("sources", [])

            if not found_count or not sources:
                continue

            if not isinstance(sources, list):
                raise ProviderError(
                    message="LeakCheck schema changed: expected list in 'sources'",
                    retryable=False,
                )

            for source in sources:
                if not isinstance(source, dict):
                    continue

                breach_name = str(source.get("name", "unknown"))
                breach_date = str(source.get("date", "unknown"))
                entries = source.get("entries", None)
                columns = source.get("columns", [])
                columns_str = (
                    ", ".join(columns)
                    if isinstance(columns, list) and columns
                    else "unknown"
                )
                entries_note = f" Approx. {entries} entries." if entries else ""

                description = (
                    f"{val} found in breach '{breach_name}' (date: {breach_date}).{entries_note} "
                    f"Exposed columns: {columns_str}."
                )

                has_password = isinstance(columns, list) and any(
                    c.lower() in {"password", "hash", "password_hash"} for c in columns
                )

                findings.append(
                    dict(
                        provider=self.name,
                        category="breach_monitor",
                        title=f"LeakCheck breach: {val} in {breach_name}",
                        description=description,
                        entity_type=_entity_type,
                        entity_value=_value,
                        tags=["breach", "leak", "leakcheck"],
                        raw={
                            "breach_name": breach_name,
                            "breach_date": breach_date,
                            "columns": columns,
                            "has_password": has_password,
                            "entries": entries,
                        },
                    )
                )

        return findings
