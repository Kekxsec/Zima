# backend/app/providers/tools/wafw00f/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_tool_wafw00f.py (MIT licensed)
# Active tool wrapper — not supported in provider mode.
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ToolWafw00fProvider(BaseProviderClient):
    name = "tool_wafw00f"

    async def detect_waf(
        self, *, domain: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        raise ProviderError(
            message="wafw00f WAF detection is not supported in provider mode — use the SpiderFoot runtime directly",
            retryable=False,
        )
