# backend/app/providers/domain/dnsbrute/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_dnsbrute.py (MIT licensed)
# Active DNS brute-forcer — not supported in provider mode.
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class DnsBruteProvider(BaseProviderClient):
    name = "dnsbrute"

    async def resolve_dns(self, domain: str) -> list[dict[str, Any]]:
        raise ProviderError(
            message="Active DNS brute-forcing is not supported in provider mode — use the SpiderFoot runtime directly",
            retryable=False,
        )
