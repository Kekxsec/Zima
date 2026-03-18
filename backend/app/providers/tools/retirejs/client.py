# backend/app/providers/tools/retirejs/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_tool_retirejs.py (MIT licensed)
# Active tool wrapper — not supported in provider mode.
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ToolRetirejsProvider(BaseProviderClient):
    name = "tool_retirejs"

    async def check_js_libraries(
        self, *, domain: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        raise ProviderError(
            message="retire.js JavaScript vulnerability scanning is not supported in provider mode — use the SpiderFoot runtime directly",
            retryable=False,
        )
