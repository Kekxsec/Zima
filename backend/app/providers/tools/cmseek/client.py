# backend/app/providers/tools/cmseek/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_tool_cmseek.py (MIT licensed)
# Active tool wrapper — not supported in provider mode.
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ToolCmseekProvider(BaseProviderClient):
    name = "tool_cmseek"

    async def scan_cms(
        self, *, domain: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        raise ProviderError(
            message="CMSeek CMS scanning is not supported in provider mode — use the SpiderFoot runtime directly",
            retryable=False,
        )
