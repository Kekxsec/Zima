# backend/app/providers/tools/onesixtyone/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_tool_onesixtyone.py (MIT licensed)
# Active tool wrapper — not supported in provider mode.
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ToolOnesixtyloneProvider(BaseProviderClient):
    name = "tool_onesixtyone"

    async def check_snmp(self, ip_address: str) -> list[dict[str, Any]]:
        raise ProviderError(
            message="onesixtyone SNMP scanning is not supported in provider mode — use the SpiderFoot runtime directly",
            retryable=False,
        )
