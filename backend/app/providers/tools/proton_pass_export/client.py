# backend/app/providers/tools/proton_pass_export/client.py
"""
ProtonPassExportProvider — parses a Proton Pass JSON vault export.

Design rules:
- Pure parser, no I/O.
- Only active login items (state=1, type="login") are extracted.
- Raw passwords are never stored — only service metadata is returned.
"""

from __future__ import annotations

import json
from typing import Any

from backend.app.providers.tools.bitwarden_export.models import VaultEntry


class ProtonPassExportProvider:
    """
    Parses Proton Pass JSON vault exports into VaultEntry objects.

    Proton Pass export structure:
        {
            "version": "1",
            "vaults": {
                "<vault-id>": {
                    "name": "Personal",
                    "items": [
                        {
                            "data": {
                                "metadata": {"name": "Service Name"},
                                "type": "login",
                                "content": {
                                    "itemEmail": "user@example.com",
                                    "itemUsername": "username",
                                    "urls": ["https://example.com"]
                                }
                            },
                            "state": 1  // 1=active, 2=trashed
                        }
                    ]
                }
            }
        }
    """

    name = "proton_pass_export"

    _ACTIVE_STATE = 1
    _LOGIN_TYPE = "login"

    def parse(self, data: bytes | str) -> list[VaultEntry]:
        """
        Parse raw Proton Pass JSON export bytes/string.

        Returns an empty list if:
        - The data is not valid JSON.
        - No active login items are present.
        """
        try:
            raw = json.loads(
                data
                if isinstance(data, str)
                else data.decode("utf-8", errors="replace")
            )
        except (json.JSONDecodeError, UnicodeDecodeError):
            return []

        if not isinstance(raw, dict):
            return []

        vaults = raw.get("vaults")
        if not isinstance(vaults, dict):
            return []

        results: list[VaultEntry] = []
        for vault in vaults.values():
            if not isinstance(vault, dict):
                continue
            items = vault.get("items")
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                # Skip trashed items
                if item.get("state") != self._ACTIVE_STATE:
                    continue
                entry = self._parse_item(item)
                if entry is not None:
                    results.append(entry)

        return results

    def _parse_item(self, item: dict[str, Any]) -> VaultEntry | None:
        try:
            data = item.get("data")
            if not isinstance(data, dict):
                return None

            if data.get("type") != self._LOGIN_TYPE:
                return None

            metadata = data.get("metadata") or {}
            service_name = (metadata.get("name") or "").strip()
            if not service_name:
                return None

            content = data.get("content") or {}
            username: str | None = (
                content.get("itemEmail") or content.get("itemUsername") or ""
            ).strip() or None

            login_url: str | None = None
            urls = content.get("urls")
            if isinstance(urls, list) and urls:
                login_url = (urls[0] or "").strip() or None

            notes = (metadata.get("note") or "").strip() or None

            return VaultEntry(
                service_name=service_name,
                username=username,
                login_url=login_url,
                notes=notes,
            )
        except Exception:
            return None
