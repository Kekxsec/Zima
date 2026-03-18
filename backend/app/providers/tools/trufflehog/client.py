# backend/app/providers/tools/trufflehog/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_tool_trufflehog.py (MIT licensed)
# Active tool wrapper — not supported in provider mode.
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ToolTrufflehogProvider(BaseProviderClient):
    name = "tool_trufflehog"

    async def scan_secrets(
        self, *, domain: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        raise ProviderError(
            message="TruffleHog secret scanning is not supported in provider mode — use the SpiderFoot runtime directly",
            retryable=False,
        )
