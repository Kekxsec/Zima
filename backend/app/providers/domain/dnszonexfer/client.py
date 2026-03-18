# backend/app/providers/domain/dnszonexfer/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_dnszonexfer.py (MIT licensed)
# Active DNS zone transfer — not supported in provider mode.
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class DnsZonexferProvider(BaseProviderClient):
    name = "dnszonexfer"

    async def resolve_dns(self, domain: str) -> list[dict[str, Any]]:
        raise ProviderError(
            message="Active DNS zone transfer (AXFR) is not supported in provider mode — use the SpiderFoot runtime directly",
            retryable=False,
        )
