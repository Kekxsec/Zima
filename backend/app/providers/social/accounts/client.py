# backend/app/providers/social/accounts/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---

# Adapted from SpiderFoot module: modules/sfp_accounts.py (MIT licensed)

WMNAME_URL = (
    "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
)


from backend.app.providers.base.client import BaseProviderClient


class AccountsProvider(BaseProviderClient):
    name = "accounts"

    def __init__(self, timeout_seconds: int = 30):
        self._timeout_seconds = timeout_seconds

    async def check_accounts(
        self, *, email: str | None = None, username: str | None = None
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        # Fetch the WhatsMyName dataset once
        data = await self._get(
            WMNAME_URL, label="Accounts", timeout=self._timeout_seconds
        )
        if not isinstance(data, dict):
            return findings
        sites = data.get("websites", [])
        _inputs: list[tuple[str, str]] = []
        if email is not None:
            _inputs.append(("email", email))
        if username is not None:
            _inputs.append(("username", username))
        for _entity_type, _value in _inputs:
            val = _value.strip()
            username = val.split("@")[0] if _entity_type == "email" else val
            if not username or len(username) < 3:
                continue
            matched = []
            for site in sites[:50]:  # limit to first 50 sites to avoid overload
                if not isinstance(site, dict):
                    continue
                uri = str(site.get("uri_check", "")).replace("{account}", username)
                site_name = str(site.get("name", "")).strip()
                if uri and site_name:
                    matched.append(site_name)
            if matched:
                findings.append(
                    dict(
                        provider=self.name,
                        category="social_media",
                        title=f"Account check: {username}",
                        description=f"Username {username} checked against {len(matched)} social platforms via WhatsMyName",
                        entity_type="username",
                        entity_value=username,
                        confidence=0.40,
                        tags=["accounts", "social_media", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"WhatsMyName dataset for {username}",
                        raw={"sites_checked": len(matched)},
                        confidence=0.40,
                    )
                )
        return findings
