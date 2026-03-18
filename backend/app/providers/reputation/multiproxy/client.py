# backend/app/providers/reputation/multiproxy/client.py
from __future__ import annotations

from typing import Any

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.MEDIUM
# --- End migration notes ---

# Adapted from SpiderFoot module: modules/sfp_multiproxy.py (MIT licensed)

PROXY_LIST_URL = "https://multiproxy.org/txt_all/proxy.txt"


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class MultiproxyProvider(BaseProviderClient):
    name = "multiproxy"

    def __init__(self, timeout_seconds: int = 30):
        self._timeout_seconds = timeout_seconds

    async def get_reputation(self, ip_address: str) -> list[dict[str, Any]]:
        findings, evidence = [], []
        try:
            resp = await self._get(PROXY_LIST_URL, timeout=self._timeout_seconds)
        except Exception as exc:
            raise ProviderError(
                message="MultiProxy list fetch failed", retryable=True
            ) from exc
        if resp.status_code != 200:
            raise ProviderError(
                message="MultiProxy list unexpected response", retryable=False
            )
        content = (
            resp.content
            if isinstance(resp.content, str)
            else resp.content.decode("utf-8", errors="replace")
        )
        proxy_ips = set()
        for line in content.splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                ip = line.split(":")[0].strip()
                if ip:
                    proxy_ips.add(ip)

        val = ip_address.strip()
        if val in proxy_ips:
            findings.append(
                dict(
                    provider=self.name,
                    category="proxy",
                    title=f"MultiProxy: {val}",
                    description=f"IP {val} is in MultiProxy open proxy list",
                    entity_type="ip_address",
                    entity_value=val,
                    confidence=0.78,
                    tags=["multiproxy", "proxy", "passive"],
                )
            )
            evidence.append(
                dict(
                    source=self.name,
                    description=f"MultiProxy match for {val}",
                    raw={"proxy": True},
                    confidence=0.78,
                )
            )
        return findings
