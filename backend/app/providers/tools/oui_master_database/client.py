# backend/app/providers/tools/oui_master_database/client.py
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from backend.app.providers.base.client import BaseProviderClient

# IEEE OUI database — bundled as a plain-text file alongside this module.
# Format: one entry per line: "XX:XX:XX   (hex)   Vendor Name"
# Download: https://standards-oui.ieee.org/oui/oui.txt
_OUI_TXT_PATH = Path(__file__).parent / "oui.txt"

_MAC_NORMALIZE_RE = re.compile(r"[^0-9a-fA-F]")


class OuiMasterDatabaseProvider(BaseProviderClient):
    """Offline IEEE OUI (Organizationally Unique Identifier) lookup.

    Maps the first three octets of a MAC address to a vendor/manufacturer
    name using the bundled oui.txt file from the IEEE registry.

    No network calls — purely offline. Returns {} if the OUI database file
    is not present (oui.txt must be placed alongside this module).
    """

    name = "oui_master_database"

    def __init__(self) -> None:
        super().__init__(timeout_seconds=5)

    async def lookup(self, mac_address: str) -> dict[str, Any]:
        """Look up the vendor for a MAC address.

        Returns dict with keys: mac, oui, vendor (or empty string on miss).
        """
        mac = mac_address.strip()
        if not mac:
            return {"mac": mac, "oui": "", "vendor": ""}

        normalized = _MAC_NORMALIZE_RE.sub("", mac).upper()
        if len(normalized) < 6:
            return {"mac": mac, "oui": "", "vendor": ""}

        oui = f"{normalized[0:2]}:{normalized[2:4]}:{normalized[4:6]}"
        vendor = _lookup_oui(oui)
        return {"mac": mac, "oui": oui, "vendor": vendor}

    async def lookup_many(self, mac_addresses: list[str]) -> list[dict[str, Any]]:
        """Bulk MAC address lookup. Returns results in input order."""
        return [await self.lookup(mac) for mac in mac_addresses]


@lru_cache(maxsize=1)
def _load_oui_db() -> dict[str, str]:
    """Load and cache the IEEE OUI database from oui.txt."""
    db: dict[str, str] = {}
    if not _OUI_TXT_PATH.exists():
        return db
    try:
        with open(_OUI_TXT_PATH, encoding="utf-8", errors="replace") as fh:
            for line in fh:
                # Lines look like: "00-00-00   (hex)		XEROX CORPORATION"
                line = line.strip()
                if "(hex)" not in line:
                    continue
                parts = line.split("(hex)")
                if len(parts) < 2:
                    continue
                raw_oui = parts[0].strip().replace("-", ":").upper()
                vendor = parts[1].strip()
                if raw_oui and vendor:
                    db[raw_oui] = vendor
    except OSError:
        pass
    return db


def _lookup_oui(oui: str) -> str:
    """Return vendor name for a colon-separated OUI prefix (e.g. 'AA:BB:CC')."""
    db = _load_oui_db()
    return db.get(oui.upper(), "")
