# backend/app/providers/tools/portscan_tcp/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_portscan_tcp.py (MIT licensed)
# Active scanner — not supported in provider mode.
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class PortscanTcpProvider(BaseProviderClient):
    name = "portscan_tcp"

    async def scan_ports(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        raise ProviderError(
            message="Active TCP port scanning is not supported in provider mode — use the SpiderFoot runtime directly",
            retryable=False,
        )
