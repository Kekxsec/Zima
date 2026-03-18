# backend/app/providers/social/pgp/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_pgp.py (MIT licensed)
import re
import urllib.parse
from typing import Any

KEYSERVER_URL = "https://keyserver.ubuntu.com/pks/lookup"


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class PgpProvider(BaseProviderClient):
    name = "pgp"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def get_pgp_keys(
        self, *, email: str | None = None, name: str | None = None
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if email is not None:
            _inputs.append(("email", email))
        if name is not None:
            _inputs.append(("name", name))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"email", "human_name"}:
                continue
            val = _value.strip()
            params = urllib.parse.urlencode(
                {"fingerprint": "on", "op": "vindex", "search": val}
            )
            url = f"{KEYSERVER_URL}?{params}"
            try:
                resp = await self._get(url, timeout=self._timeout_seconds)
            except Exception as exc:
                raise ProviderError(
                    message="PGP keyserver request failed", retryable=True
                ) from exc
            if resp.status_code == 404:
                continue
            if resp.status_code == 429:
                raise ProviderError(
                    message="PGP keyserver rate limited", retryable=True
                )
            if resp.status_code != 200:
                raise ProviderError(
                    message="PGP keyserver unexpected response", retryable=False
                )
            content = (
                resp.content
                if isinstance(resp.content, str)
                else resp.content.decode("utf-8", errors="replace")
            )
            # Extract key IDs and UIDs from HTML
            key_ids = re.findall(r"pub\s+\w+/([0-9A-F]+)", content)
            uids = re.findall(r"uid\s+([^<\n]+?)(?:<|$)", content)
            if key_ids:
                for kid in key_ids[:5]:
                    if kid in seen:
                        continue
                    seen.add(kid)
                    findings.append(
                        dict(
                            provider=self.name,
                            category="pgp_key",
                            title=f"PGP key: {val}",
                            description=f"PGP key found for {val}: key ID {kid}",
                            entity_type=_entity_type,
                            entity_value=val,
                            confidence=0.85,
                            tags=["pgp", "cryptography", "passive"],
                        )
                    )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"PGP keys for {val}",
                        raw={
                            "key_ids": key_ids[:5],
                            "uids": [u.strip() for u in uids[:3]],
                        },
                        confidence=0.85,
                    )
                )
        return findings
