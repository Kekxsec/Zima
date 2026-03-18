# backend/app/providers/tools/snallygaster/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_tool_snallygaster.py (MIT licensed)
# Active tool wrapper — not supported in provider mode.
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ToolSnallygasterProvider(BaseProviderClient):
    name = "tool_snallygaster"

    async def check_misconfigs(self, domain: str) -> list[dict[str, Any]]:
        raise ProviderError(
            message="snallygaster secret file scanning is not supported in provider mode — use the SpiderFoot runtime directly",
            retryable=False,
        )
