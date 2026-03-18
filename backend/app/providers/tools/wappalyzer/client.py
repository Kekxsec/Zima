# backend/app/providers/tools/wappalyzer/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_tool_wappalyzer.py (MIT licensed)
# Active tool wrapper — not supported in provider mode.
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ToolWappalyzerProvider(BaseProviderClient):
    name = "tool_wappalyzer"

    async def detect_technologies(
        self, *, domain: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        raise ProviderError(
            message="Wappalyzer technology detection is not supported in provider mode — use the SpiderFoot runtime directly",
            retryable=False,
        )
