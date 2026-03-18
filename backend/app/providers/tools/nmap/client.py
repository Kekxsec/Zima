# backend/app/providers/tools/nmap/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_tool_nmap.py (MIT licensed)
# Active tool wrapper — not supported in provider mode.
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ToolNmapProvider(BaseProviderClient):
    name = "tool_nmap"

    async def scan_ports(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        raise ProviderError(
            message="nmap active port scanning is not supported in provider mode — use the SpiderFoot runtime directly",
            retryable=False,
        )
