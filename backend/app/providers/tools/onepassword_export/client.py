# backend/app/providers/tools/onepassword_export/client.py
"""
OnePasswordExportProvider — parses a 1Password .1pux vault export.

Design rules:
- Pure parser, no I/O.
- .1pux is a ZIP archive containing export.data (JSON).
- Only Login items (categoryUuid="001") in active state are extracted.
- Raw passwords are never stored — only service metadata is returned.
"""

from __future__ import annotations

import io
import json
import zipfile
from typing import Any

from backend.app.providers.tools.bitwarden_export.models import VaultEntry

_EXPORT_DATA_PATH = "export.data"
_LOGIN_CATEGORY = "001"
_MAX_EXPORT_DATA_BYTES = 25 * 1024 * 1024
_MAX_COMPRESSION_RATIO = 100


class OnePasswordExportProvider:
    """
    Parses 1Password .1pux vault exports into VaultEntry objects.

    .1pux structure:
        ZIP archive containing export.data (JSON):
        {
            "accounts": [
                {
                    "vaults": [
                        {
                            "items": [
                                {
                                    "categoryUuid": "001",  // 001=Login
                                    "state": "active",
                                    "overview": {
                                        "title": "Service Name",
                                        "url": "https://example.com",
                                        "urls": [{"u": "https://example.com"}]
                                    },
                                    "details": {
                                        "loginFields": [
                                            {
                                                "designation": "username",
                                                "value": "user@example.com"
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    """

    name = "onepassword_export"

    def parse(self, data: bytes) -> list[VaultEntry]:
        """
        Parse raw .1pux archive bytes.

        Returns an empty list if:
        - The data is not a valid ZIP archive.
        - export.data is missing or not valid JSON.
        - No active login items are present.
        """
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                if _EXPORT_DATA_PATH not in zf.namelist():
                    return []
                info = zf.getinfo(_EXPORT_DATA_PATH)
                if info.file_size > _MAX_EXPORT_DATA_BYTES:
                    return []
                compressed_size = max(info.compress_size, 1)
                if info.file_size / compressed_size > _MAX_COMPRESSION_RATIO:
                    return []
                export_data = zf.read(_EXPORT_DATA_PATH)
        except (zipfile.BadZipFile, zipfile.LargeZipFile, KeyError, OSError):
            return []

        try:
            raw = json.loads(export_data.decode("utf-8", errors="replace"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return []

        if not isinstance(raw, dict):
            return []

        accounts = raw.get("accounts")
        if not isinstance(accounts, list):
            return []

        results: list[VaultEntry] = []
        for account in accounts:
            if not isinstance(account, dict):
                continue
            vaults = account.get("vaults")
            if not isinstance(vaults, list):
                continue
            for vault in vaults:
                if not isinstance(vault, dict):
                    continue
                items = vault.get("items")
                if not isinstance(items, list):
                    continue
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    if item.get("state") != "active":
                        continue
                    if item.get("categoryUuid") != _LOGIN_CATEGORY:
                        continue
                    entry = self._parse_item(item)
                    if entry is not None:
                        results.append(entry)

        return results

    def _parse_item(self, item: dict[str, Any]) -> VaultEntry | None:
        try:
            overview = item.get("overview") or {}
            service_name = (overview.get("title") or "").strip()
            if not service_name:
                return None

            # Prefer first entry from urls list; fall back to top-level url
            login_url: str | None = None
            urls = overview.get("urls")
            if isinstance(urls, list) and urls:
                first = urls[0]
                if isinstance(first, dict):
                    login_url = (first.get("u") or "").strip() or None
            if not login_url:
                login_url = (overview.get("url") or "").strip() or None

            # Extract username from loginFields
            username: str | None = None
            details = item.get("details") or {}
            login_fields = details.get("loginFields")
            if isinstance(login_fields, list):
                for field in login_fields:
                    if (
                        isinstance(field, dict)
                        and field.get("designation") == "username"
                    ):
                        username = (field.get("value") or "").strip() or None
                        break

            notes = (details.get("notesPlain") or "").strip() or None

            return VaultEntry(
                service_name=service_name,
                username=username,
                login_url=login_url,
                notes=notes,
            )
        except Exception:
            return None
