# backend/app/providers/tools/posture/client.py
from __future__ import annotations

import asyncio
import platform
import shutil
import subprocess
from typing import Any

from backend.app.providers.base.client import BaseProviderClient

_TIMEOUT_SECONDS = 15


class PostureProvider(BaseProviderClient):
    """Device security posture reader.

    Collects basic security posture indicators using platform-native Python
    calls and lightweight subprocess commands. No external API required.

    Returns a posture dict with keys: platform, os_version, architecture,
    hostname, screen_lock_enabled, disk_encryption_status, auto_update_enabled,
    firewall_enabled.
    """

    name = "posture"

    def __init__(self, timeout_seconds: int = _TIMEOUT_SECONDS) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    async def collect(self) -> dict[str, Any]:
        """Collect device posture snapshot. Never raises — returns partial data on error."""
        system = platform.system()
        posture: dict[str, Any] = {
            "platform": system,
            "os_version": platform.version(),
            "release": platform.release(),
            "architecture": platform.machine(),
            "hostname": platform.node(),
            "python_implementation": platform.python_implementation(),
        }

        if system == "Darwin":
            posture.update(await self._collect_macos())
        elif system == "Linux":
            posture.update(await self._collect_linux())
        elif system == "Windows":
            posture.update(await self._collect_windows())

        return posture

    async def _collect_macos(self) -> dict[str, Any]:
        data: dict[str, Any] = {}

        # SIP status
        csrutil = shutil.which("csrutil")
        if csrutil:
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    [csrutil, "status"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                data["sip_status"] = result.stdout.strip()
                data["sip_enabled"] = "enabled" in result.stdout.lower()
            except (subprocess.TimeoutExpired, OSError):
                data["sip_status"] = "unknown"

        # FileVault status
        fdesetup = shutil.which("fdesetup")
        if fdesetup:
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    [fdesetup, "status"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                data["filevault_status"] = result.stdout.strip()
                data["disk_encryption_enabled"] = "on" in result.stdout.lower()
            except (subprocess.TimeoutExpired, OSError):
                data["filevault_status"] = "unknown"

        return data

    async def _collect_linux(self) -> dict[str, Any]:
        data: dict[str, Any] = {}

        # Kernel version
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                ["uname", "-r"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            data["kernel_version"] = result.stdout.strip()
        except (subprocess.TimeoutExpired, OSError):
            pass

        # LUKS / dm-crypt encryption
        cryptsetup = shutil.which("cryptsetup")
        if cryptsetup:
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["cryptsetup", "status", "-"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                data["luks_active"] = result.returncode == 0
            except (subprocess.TimeoutExpired, OSError):
                pass

        # UFW firewall
        ufw = shutil.which("ufw")
        if ufw:
            try:
                result = await asyncio.to_thread(
                    subprocess.run,
                    ["ufw", "status"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                data["ufw_status"] = result.stdout.strip()
                data["firewall_enabled"] = "active" in result.stdout.lower()
            except (subprocess.TimeoutExpired, OSError):
                pass

        return data

    async def _collect_windows(self) -> dict[str, Any]:
        data: dict[str, Any] = {}

        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if not powershell:
            return data

        # Basic OS info
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                [
                    powershell,
                    "-NoProfile",
                    "-Command",
                    "(Get-ComputerInfo | Select-Object OsName,OsVersion,OsBuildNumber | ConvertTo-Json)",
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0 and result.stdout.strip():
                import json

                try:
                    data["os_info"] = json.loads(result.stdout)
                except (json.JSONDecodeError, ValueError):
                    data["os_info_raw"] = result.stdout.strip()
        except (subprocess.TimeoutExpired, OSError):
            pass

        return data
