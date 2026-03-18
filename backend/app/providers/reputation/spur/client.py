# backend/app/providers/reputation/spur/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_spur.py (MIT licensed)
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class SpurProvider(BaseProviderClient):
    name = "spur"
    base_url = "https://api.spur.us/v2/context"

    def __init__(self, api_token: str = "", timeout_seconds: int = 15):
        self._api_token = api_token
        self._timeout_seconds = timeout_seconds

    async def get_reputation(self, ip_address: str) -> list[dict[str, Any]]:
        api_token = str(self._api_token).strip()
        if not api_token:
            raise ProviderError(message="Spur API token is required", retryable=False)
        headers = {"Token": api_token, "Accept": "application/json"}
        findings, evidence = [], []
        val = ip_address.strip()
        url = f"{self.base_url}/{val}"
        data = self._fetch(url, headers)
        if not isinstance(data, dict):
            return findings
        proxies = data.get("proxies", {}) or {}
        tunnels = data.get("tunnels", []) or []
        vpn = isinstance(proxies, dict) and (proxies.get("vpn") or proxies.get("proxy"))
        if vpn or tunnels:
            tunnel_types = [
                str(t.get("type", "")) for t in tunnels[:3] if isinstance(t, dict)
            ]
            desc = f"IP {val} is"
            if vpn:
                desc += " a VPN/proxy"
            if tunnels:
                desc += f" tunnel types: {', '.join(tunnel_types)}"
            findings.append(
                dict(
                    provider=self.name,
                    category="proxy",
                    title=f"Spur: {val}",
                    description=desc,
                    entity_type="ip_address",
                    entity_value=val,
                    confidence=0.82,
                    tags=["spur", "proxy", "vpn", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"Spur context for {val}",
                    raw={"vpn": bool(vpn), "tunnels": len(tunnels)},
                    confidence=0.82,
                )
            )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Spur", headers=headers, timeout=self._timeout_seconds
        )
