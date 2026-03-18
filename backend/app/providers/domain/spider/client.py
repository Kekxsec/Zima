# backend/app/providers/domain/spider/client.py
from __future__ import annotations

from typing import Any

# Adapted from SpiderFoot module: modules/sfp_spider.py (MIT licensed)
# Active web crawler — not supported in provider mode.
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class SpiderProvider(BaseProviderClient):
    name = "spider"

    async def crawl_site(
        self, *, domain: str | None = None, url: str | None = None
    ) -> list[dict[str, Any]]:
        raise ProviderError(
            message="Active web crawling is not supported in provider mode — use the SpiderFoot runtime directly",
            retryable=False,
        )
