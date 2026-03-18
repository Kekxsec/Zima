# backend/app/providers/tools/nbtscan/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_tool_nbtscan.py (MIT licensed)
# Active tool wrapper — not supported in provider mode.
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ToolNbtscanProvider(BaseProviderClient):
    name = "tool_nbtscan"

    async def scan_netbios(self, ip_address: str) -> list[dict[str, Any]]:
        raise ProviderError(
            message="nbtscan NetBIOS scanning is not supported in provider mode — use the SpiderFoot runtime directly",
            retryable=False,
        )
