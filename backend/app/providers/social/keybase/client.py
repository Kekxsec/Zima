# backend/app/providers/social/keybase/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_keybase.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class KeybaseProvider(BaseProviderClient):
    name = "keybase"
    base_url = "https://keybase.io/_/api/1.0/user/lookup.json"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def search_social(
        self, *, email: str | None = None, username: str | None = None
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if email is not None:
            _inputs.append(("email", email))
        if username is not None:
            _inputs.append(("username", username))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"username", "email"}:
                continue
            val = _value.strip()
            if _entity_type == "email":
                params = urllib.parse.urlencode({"email": val})
            else:
                params = urllib.parse.urlencode({"usernames": val})
            url = f"{self.base_url}?{params}"
            data = self._fetch(url)
            if not isinstance(data, dict):
                continue
            status = data.get("status", {})
            if isinstance(status, dict) and status.get("code") != 0:
                continue
            them = (
                data.get("them", [])
                if isinstance(data.get("them"), list)
                else [data.get("them")]
                if data.get("them")
                else []
            )
            for user in them:
                if not isinstance(user, dict):
                    continue
                username = str(
                    user.get("basics", {}).get("username", "")
                    if isinstance(user.get("basics"), dict)
                    else ""
                ).strip()
                if not username:
                    continue
                proofs = (
                    user.get("proofs_summary", {}).get("all", [])
                    if isinstance(user.get("proofs_summary"), dict)
                    else []
                )
                proof_services = list(
                    {
                        str(p.get("proof_type", ""))
                        for p in proofs
                        if isinstance(p, dict)
                    }
                )
                findings.append(
                    dict(
                        provider=self.name,
                        category="social_media",
                        title=f"Keybase: {username}",
                        description=f"Keybase account found: {username}"
                        + (
                            f", verified on: {', '.join(proof_services)}"
                            if proof_services
                            else ""
                        ),
                        entity_type="username",
                        entity_value=username,
                        confidence=0.82,
                        tags=["keybase", "social_media", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Keybase profile for {val}",
                        raw={"username": username, "proofs": proof_services},
                        confidence=0.82,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> dict:
        return await self._get(url, label="Keybase", timeout=self._timeout_seconds)
