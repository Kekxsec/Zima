# backend/app/providers/tools/testsslsh/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_tool_testsslsh.py (MIT licensed)
# Active tool wrapper — not supported in provider mode.
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ToolTestsslshProvider(BaseProviderClient):
    name = "tool_testsslsh"

    async def test_ssl(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        raise ProviderError(
            message="testssl.sh SSL scanning is not supported in provider mode — use the SpiderFoot runtime directly",
            retryable=False,
        )
