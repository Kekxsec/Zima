# backend/app/providers/tools/linux_native/client.py
from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Any

from backend.app.providers.base.client import BaseProviderClient

_TIMEOUT_SECONDS = 15


class LinuxNativeProvider(BaseProviderClient):
    """Linux-native security data collector.

    Reads kernel version, distro info, SELinux/AppArmor status, UFW/firewalld
    state, and automatic update settings. No network calls. Returns {} on
    non-Linux systems.
    """

    name = "linux_native"

    def __init__(self, timeout_seconds: int = _TIMEOUT_SECONDS) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    async def collect(self) -> dict[str, Any]:
        """Collect Linux security baseline. Returns {} on non-Linux systems."""
        import platform

        if platform.system() != "Linux":
            return {}

        results: dict[str, Any] = {}
        results["kernel"] = await self._kernel_version()
        results["distro"] = await self._distro_info()
        results["selinux"] = await self._selinux_status()
        results["apparmor"] = await self._apparmor_status()
        results["firewall"] = await self._firewall_status()
        results["auto_updates"] = await self._auto_update_status()
        return results

    async def _run(self, cmd: list[str], timeout: int = 5) -> str:
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout.strip()
        except (subprocess.TimeoutExpired, OSError):
            return ""

    async def _kernel_version(self) -> dict[str, str]:
        version = await self._run(["uname", "-r"])
        full = await self._run(["uname", "-a"])
        return {"version": version, "full": full}

    async def _distro_info(self) -> dict[str, str]:
        os_release = Path("/etc/os-release")
        if os_release.exists():
            try:
                content = os_release.read_text()
                data: dict[str, str] = {}
                for line in content.splitlines():
                    if "=" in line:
                        k, _, v = line.partition("=")
                        data[k.strip()] = v.strip().strip('"')
                return data
            except OSError:
                pass
        return {}

    async def _selinux_status(self) -> dict[str, Any]:
        binary = shutil.which("getenforce")
        if binary:
            raw = await self._run([binary])
            return {
                "available": True,
                "status": raw,
                "enforcing": raw.lower() == "enforcing",
            }
        selinux_path = Path("/sys/fs/selinux")
        if selinux_path.exists():
            return {"available": True, "status": "unknown"}
        return {"available": False}

    async def _apparmor_status(self) -> dict[str, Any]:
        binary = shutil.which("apparmor_status") or shutil.which("aa-status")
        if not binary:
            return {"available": False}
        raw = await self._run([binary, "--enabled"])
        return {"available": True, "enabled": raw == "" or "0" not in raw}

    async def _firewall_status(self) -> dict[str, Any]:
        # UFW
        ufw = shutil.which("ufw")
        if ufw:
            raw = await self._run(["ufw", "status"])
            return {"tool": "ufw", "status": raw, "enabled": "active" in raw.lower()}
        # firewalld
        firewalld = shutil.which("firewall-cmd")
        if firewalld:
            raw = await self._run(["firewall-cmd", "--state"])
            return {
                "tool": "firewalld",
                "status": raw,
                "enabled": raw.lower() == "running",
            }
        # iptables fallback
        iptables = shutil.which("iptables")
        if iptables:
            raw = await self._run(["iptables", "-L", "-n", "--line-numbers"])
            return {"tool": "iptables", "available": True, "raw_lines": raw.count("\n")}
        return {"available": False}

    async def _auto_update_status(self) -> dict[str, Any]:
        # unattended-upgrades (Debian/Ubuntu)
        config_path = Path("/etc/apt/apt.conf.d/20auto-upgrades")
        if config_path.exists():
            try:
                content = config_path.read_text()
                enabled = "1" in content
                return {
                    "tool": "unattended-upgrades",
                    "enabled": enabled,
                    "raw": content[:200],
                }
            except OSError:
                pass
        # dnf-automatic (RHEL/CentOS/Fedora)
        dnf_timer = Path("/etc/systemd/system/dnf-automatic.timer")
        if dnf_timer.exists():
            return {"tool": "dnf-automatic", "enabled": True}
        return {"configured": False}
