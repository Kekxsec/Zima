# backend/app/providers/tools/macos_native/client.py
from __future__ import annotations

import asyncio
import shutil
import subprocess
from typing import Any

from backend.app.providers.base.client import BaseProviderClient

_TIMEOUT_SECONDS = 15


class MacOsNativeProvider(BaseProviderClient):
    """macOS-native security data collector.

    Reads OS version, SIP status, FileVault status, Gatekeeper, and
    auto-update settings using macOS system commands. No network calls.
    Only functional on macOS — returns empty dicts on other platforms.
    """

    name = "macos_native"

    def __init__(self, timeout_seconds: int = _TIMEOUT_SECONDS) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    async def collect(self) -> dict[str, Any]:
        """Collect macOS security baseline. Returns {} on non-macOS systems."""
        import platform

        if platform.system() != "Darwin":
            return {}

        results: dict[str, Any] = {}
        results["os_version"] = await self._sw_vers()
        results["sip"] = await self._sip_status()
        results["filevault"] = await self._filevault_status()
        results["gatekeeper"] = await self._gatekeeper_status()
        results["auto_update"] = await self._auto_update_status()
        return results

    async def _sw_vers(self) -> dict[str, Any]:
        """Returns macOS version info via sw_vers."""
        binary = shutil.which("sw_vers")
        if not binary:
            return {}
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [binary],
                capture_output=True,
                text=True,
                timeout=5,
            )
            data: dict[str, str] = {}
            for line in result.stdout.splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    data[key.strip()] = val.strip()
            return data
        except (subprocess.TimeoutExpired, OSError):
            return {}

    async def _sip_status(self) -> dict[str, Any]:
        """Returns SIP (System Integrity Protection) status."""
        binary = shutil.which("csrutil")
        if not binary:
            return {"available": False}
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [binary, "status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            raw = result.stdout.strip()
            enabled = "enabled" in raw.lower()
            return {"raw": raw, "enabled": enabled}
        except (subprocess.TimeoutExpired, OSError):
            return {"available": False}

    async def _filevault_status(self) -> dict[str, Any]:
        """Returns FileVault disk encryption status."""
        binary = shutil.which("fdesetup")
        if not binary:
            return {"available": False}
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [binary, "status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            raw = result.stdout.strip()
            enabled = "on" in raw.lower() and "off" not in raw.lower()
            return {"raw": raw, "enabled": enabled}
        except (subprocess.TimeoutExpired, OSError):
            return {"available": False}

    async def _gatekeeper_status(self) -> dict[str, Any]:
        """Returns Gatekeeper status via spctl."""
        binary = shutil.which("spctl")
        if not binary:
            return {"available": False}
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [binary, "--status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            raw = result.stdout.strip() or result.stderr.strip()
            enabled = "enabled" in raw.lower() or "assessments enabled" in raw.lower()
            return {"raw": raw, "enabled": enabled}
        except (subprocess.TimeoutExpired, OSError):
            return {"available": False}

    async def _auto_update_status(self) -> dict[str, Any]:
        """Returns automatic macOS software update settings."""
        binary = shutil.which("defaults")
        if not binary:
            return {"available": False}
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [
                    binary,
                    "read",
                    "/Library/Preferences/com.apple.SoftwareUpdate",
                    "AutomaticCheckEnabled",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            raw = result.stdout.strip()
            enabled = raw == "1"
            return {"AutomaticCheckEnabled": raw, "enabled": enabled}
        except (subprocess.TimeoutExpired, OSError):
            return {"available": False}
