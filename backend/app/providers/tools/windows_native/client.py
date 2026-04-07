# backend/app/providers/tools/windows_native/client.py
from __future__ import annotations

import asyncio
import json
import shutil
import subprocess
from typing import Any

from backend.app.providers.base.client import BaseProviderClient

_TIMEOUT_SECONDS = 20


class WindowsNativeProvider(BaseProviderClient):
    """Windows-native security data collector.

    Reads OS info, patch status, BitLocker, and Windows Defender state using
    PowerShell. No network calls. Returns empty dicts on non-Windows systems.
    """

    name = "windows_native"

    def __init__(self, timeout_seconds: int = _TIMEOUT_SECONDS) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    async def collect(self) -> dict[str, Any]:
        """Collect Windows security baseline. Returns {} on non-Windows systems."""
        import platform

        if platform.system() != "Windows":
            return {}

        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if not powershell:
            return {}

        results: dict[str, Any] = {}
        results["os_info"] = await self._os_info(powershell)
        results["hotfixes"] = await self._hotfixes(powershell)
        results["bitlocker"] = await self._bitlocker(powershell)
        results["defender"] = await self._defender(powershell)
        return results

    async def _ps_json(self, powershell: str, command: str) -> Any:
        """Run a PowerShell command that outputs JSON. Returns parsed result or None."""
        cmd = [
            powershell,
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            command,
        ]
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout_seconds,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None
            return json.loads(result.stdout)
        except (subprocess.TimeoutExpired, OSError, json.JSONDecodeError):
            return None

    async def _os_info(self, powershell: str) -> dict[str, Any]:
        data = await self._ps_json(
            powershell,
            "Get-ComputerInfo | Select-Object OsName,OsVersion,OsBuildNumber,WindowsVersion | ConvertTo-Json",
        )
        return data if isinstance(data, dict) else {}

    async def _hotfixes(self, powershell: str) -> list[dict[str, Any]]:
        data = await self._ps_json(
            powershell,
            "Get-HotFix | Select-Object HotFixID,InstalledOn | Sort-Object InstalledOn -Descending | Select-Object -First 20 | ConvertTo-Json",
        )
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
        return []

    async def _bitlocker(self, powershell: str) -> dict[str, Any]:
        data = await self._ps_json(
            powershell,
            "Get-BitLockerVolume | Select-Object MountPoint,ProtectionStatus,EncryptionMethod | ConvertTo-Json",
        )
        if isinstance(data, list):
            return {"volumes": data}
        if isinstance(data, dict):
            return {"volumes": [data]}
        return {}

    async def _defender(self, powershell: str) -> dict[str, Any]:
        data = await self._ps_json(
            powershell,
            "Get-MpComputerStatus | Select-Object AntivirusEnabled,RealTimeProtectionEnabled,AntivirusSignatureLastUpdated | ConvertTo-Json",
        )
        return data if isinstance(data, dict) else {}
