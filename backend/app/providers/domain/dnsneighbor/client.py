# backend/app/providers/domain/dnsneighbor/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_dnsneighbor.py (MIT licensed)
# Copyright (c) Steve Micallef.
# Active reverse DNS neighborhood scan — stubbed in provider mode.
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class DnsNeighborProvider(BaseProviderClient):
    name = "dnsneighbor"

    async def resolve_dns(self, ip_address: str) -> list[dict[str, Any]]:
        raise ProviderError(
            message="Active reverse DNS neighborhood scanning is not supported in provider mode — use the SpiderFoot runtime directly",
            retryable=False,
        )
