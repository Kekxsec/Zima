# backend/app/providers/tools/bitwarden_export/client.py
"""
BitwardenExportProvider — parses a Bitwarden JSON vault export.

Design rules:
- Pure parser, no I/O.
- Only Login items (type=1) are extracted; SecureNote/Card/Identity are skipped.
- Encrypted exports are rejected immediately (no key available server-side).
- Raw passwords are never stored — only service metadata is returned.
"""

from __future__ import annotations

import json
from typing import Any

from backend.app.providers.tools.bitwarden_export.models import VaultEntry


class BitwardenExportProvider:
    """
    Parses Bitwarden unencrypted JSON vault exports into VaultEntry objects.

    Bitwarden export structure:
        {
            "encrypted": false,
            "folders": [...],
            "items": [
                {
                    "type": 1,              // 1=Login (only type we process)
                    "name": "Service Name",
                    "login": {
                        "uris": [{"uri": "https://example.com"}],
                        "username": "user@example.com"
                    }
                }
            ]
        }
    """

    name = "bitwarden_export"

    _LOGIN_TYPE = 1

    def parse(self, data: bytes | str) -> list[VaultEntry]:
        """
        Parse raw Bitwarden JSON export bytes/string.

        Returns an empty list if:
        - The data is not valid JSON.
        - The export is encrypted.
        - No login items are present.
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

        if raw.get("encrypted"):
            return []

        items = raw.get("items")
        if not isinstance(items, list):
            return []

        results: list[VaultEntry] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("type") != self._LOGIN_TYPE:
                continue
            entry = self._parse_item(item)
            if entry is not None:
                results.append(entry)

        return results

    def _parse_item(self, item: dict[str, Any]) -> VaultEntry | None:
        try:
            service_name = (item.get("name") or "").strip()
            if not service_name:
                return None

            login = item.get("login") or {}
            username = (login.get("username") or "").strip() or None

            login_url: str | None = None
            uris = login.get("uris")
            if isinstance(uris, list) and uris:
                first_uri = uris[0]
                if isinstance(first_uri, dict):
                    login_url = (first_uri.get("uri") or "").strip() or None

            notes = (item.get("notes") or "").strip() or None

            return VaultEntry(
                service_name=service_name,
                username=username,
                login_url=login_url,
                notes=notes,
            )
        except Exception:
            return None
