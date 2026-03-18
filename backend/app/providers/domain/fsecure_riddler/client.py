# backend/app/providers/domain/fsecure_riddler/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_fsecure_riddler.py (MIT licensed)
import json
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class FsecureRiddlerProvider(BaseProviderClient):
    name = "fsecure_riddler"
    base_url = "https://riddler.io/api/search"

    def __init__(
        self, api_user: str = "", api_password: str = "", timeout_seconds: int = 15
    ):
        self._api_user = api_user
        self._api_password = api_password
        self._timeout_seconds = timeout_seconds

    async def lookup_domain(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        api_user = str(self._api_user).strip()
        api_pass = str(self._api_password).strip()
        if not api_user or not api_pass:
            raise ProviderError(
                message="Riddler username and password are required", retryable=False
            )
        # Login to get auth token
        try:
            login_resp = await self._post(
                "https://riddler.io/auth/login",
                data=json.dumps({"email": api_user, "password": api_pass}),
                headers={"Content-Type": "application/json"},
                timeout=self._timeout_seconds,
            )
        except Exception as exc:
            raise ProviderError(message="Riddler login failed", retryable=True) from exc
        if login_resp.status_code in {401, 403}:
            raise ProviderError(
                message="Riddler rejected credentials",
                retryable=False,
                status_code=login_resp.status_code,
            )
        try:
            login_data = json.loads(login_resp.content)
            token = (
                login_data.get("response", {})
                .get("user", {})
                .get("authentication_token", "")
            )
        except Exception:
            token = ""
        if not token:
            raise ProviderError(
                message="Riddler login token not found", retryable=False
            )
        headers = {"Authentication-Token": token, "Content-Type": "application/json"}
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "ip_address"}:
                continue
            val = _value.strip()
            query = f"pld:{val}" if _entity_type == "domain" else f"ip:{val}"
            payload = {"query": query, "limit": 20}
            data = self._fetch_post(self.base_url, headers, payload)
            results = data if isinstance(data, list) else []
            for item in results[:20]:
                if not isinstance(item, dict):
                    continue
                host = str(item.get("host", "")).strip()
                ip = str(item.get("ip", "")).strip()
                key = host or ip
                if not key or key in seen:
                    continue
                seen.add(key)
                findings.append(
                    dict(
                        provider=self.name,
                        category="network_info",
                        title=f"Riddler: {key}",
                        description=f"Riddler result for {val}: {key}"
                        + (f" ({ip})" if host and ip else ""),
                        entity_type="hostname",
                        entity_value=key,
                        confidence=0.72,
                        tags=["riddler", "passive_dns", "passive"],
                    )
                )
            if results:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Riddler results for {val}",
                        raw={"count": len(results)},
                        confidence=0.72,
                    )
                )
        return findings

    async def _fetch_post(self, url: str, headers: dict, payload: dict) -> dict:
        return await self._post(
            url,
            json_data=payload,
            label="FsecureRiddler",
            headers=headers,
            timeout=self._timeout_seconds,
        )
