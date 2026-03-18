# backend/app/providers/tools/nuclei/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_tool_nuclei.py (MIT licensed)
# Active tool wrapper — not supported in provider mode.
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ToolNucleiProvider(BaseProviderClient):
    name = "tool_nuclei"

    async def scan_vulnerabilities(
        self, *, domain: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        raise ProviderError(
            message="nuclei vulnerability scanning is not supported in provider mode — use the SpiderFoot runtime directly",
            retryable=False,
        )
