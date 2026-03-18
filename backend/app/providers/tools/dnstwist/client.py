# backend/app/providers/tools/dnstwist/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_tool_dnstwist.py (MIT licensed)
# Active tool wrapper — not supported in provider mode.
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ToolDnstwistProvider(BaseProviderClient):
    name = "tool_dnstwist"

    async def find_typosquats(self, domain: str) -> list[dict[str, Any]]:
        raise ProviderError(
            message="dnstwist domain permutation scanning is not supported in provider mode — use the SpiderFoot runtime directly",
            retryable=False,
        )
