# backend/app/providers/cloud/firefox_addons_site_api/client.py
from __future__ import annotations

from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class FirefoxAddonsSiteApiProvider(BaseProviderClient):
    """Mozilla AMO (addons.mozilla.org) public API v5.

    Official public API — no authentication required for listed add-ons.
    Enrichment-only — does NOT emit signals directly.
    """

    name = "firefox_addons_site_api"
    base_url = "https://addons.mozilla.org/api/v5"

    def __init__(self, timeout_seconds: int = 15) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    async def get_addon(self, guid: str) -> dict[str, Any] | None:
        """Fetch AMO add-on metadata for a given GUID, slug, or numeric ID.

        GET /api/v5/addons/addon/{guid}/
        Returns enrichment dict or None on 404.
        Key enrichment fields: guid, name, status, promoted, average_daily_users,
        ratings.average, last_updated, is_experimental, has_privacy_policy.
        """
        identifier = guid.strip()
        if not identifier:
            return None

        url = f"{self.base_url}/addons/addon/{identifier}/"
        data = await self._get(
            url,
            label="FirefoxAddonsSiteApi",
            headers={"Accept": "application/json"},
        )
        if not data or not isinstance(data, dict):
            return None

        ratings = data.get("ratings") or {}
        promoted = data.get("promoted") or {}
        return {
            "guid": data.get("guid"),
            "slug": data.get("slug"),
            "name": (data.get("name") or {}).get("en-US"),
            "status": data.get("status"),
            "promoted_category": promoted.get("category"),
            "average_daily_users": data.get("average_daily_users"),
            "ratings_average": ratings.get("average"),
            "ratings_count": ratings.get("count"),
            "last_updated": data.get("last_updated"),
            "is_experimental": data.get("is_experimental"),
            "has_privacy_policy": data.get("has_privacy_policy"),
            "store_url": f"https://addons.mozilla.org/addon/{data.get('slug', identifier)}",
            "raw": data,
        }

    async def get_version_detail(
        self, addon_id: str | int, version_id: int
    ) -> dict[str, Any] | None:
        """Fetch version-level detail including permissions.

        GET /api/v5/addons/addon/{addon_id}/versions/{version_id}/
        Key fields: file.permissions, file.optional_permissions, file.host_permissions.
        Returns enrichment dict or None on 404.
        """
        url = f"{self.base_url}/addons/addon/{addon_id}/versions/{version_id}/"
        data = await self._get(
            url,
            label="FirefoxAddonsSiteApi",
            headers={"Accept": "application/json"},
        )
        if not data or not isinstance(data, dict):
            return None

        file_info = data.get("file") or {}
        return {
            "version": data.get("version"),
            "permissions": file_info.get("permissions", []),
            "optional_permissions": file_info.get("optional_permissions", []),
            "host_permissions": file_info.get("host_permissions", []),
            "raw": data,
        }
