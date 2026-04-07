# backend/app/providers/tools/lynis/client.py
from __future__ import annotations

import asyncio
import os
import shutil
import signal
import subprocess
from pathlib import Path
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import ProviderError

_TOOL_NAME = "lynis"
_TIMEOUT_SECONDS = 120
_REPORT_PATHS = [
    "/var/log/lynis-report.dat",
    "/tmp/lynis-report.dat",  # noqa: S108
]

# Report key prefixes we extract
_SUGGESTION_PREFIX = "suggestion[]="
_WARNING_PREFIX = "warning[]="
_OS_KEY = "os[]="
_HARDENING_INDEX_KEY = "hardening_index="


class LynisProvider(BaseProviderClient):
    """Lynis security audit runner.

    Runs ``lynis audit system --cronjob --quiet`` and parses the report file
    at /var/log/lynis-report.dat. Returns structured findings.

    Requires lynis to be installed:
        https://cisofy.com/lynis/
    """

    name = "lynis"

    def __init__(self, timeout_seconds: int = _TIMEOUT_SECONDS) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    async def audit(self) -> dict[str, Any]:
        """Run a lynis system audit and parse results.

        Returns dict with keys:
          - hardening_index: int (0-100)
          - suggestions: list[str]
          - warnings: list[str]
          - os: str
          - raw_report_path: str | None
        """
        binary = shutil.which(_TOOL_NAME)
        if not binary:
            raise ProviderError(
                message=(
                    "lynis is not installed or not in PATH. "
                    "Install: https://cisofy.com/lynis/"
                ),
                retryable=False,
            )

        report_path = await self._run_audit(binary)
        if not report_path:
            # Try to read an existing report from default locations
            for path in _REPORT_PATHS:
                if Path(path).exists():
                    report_path = path
                    break

        if not report_path or not Path(report_path).exists():
            raise ProviderError(
                message="lynis audit completed but report file not found",
                retryable=False,
            )

        return await asyncio.to_thread(self._parse_report, report_path)

    async def _run_audit(self, binary: str) -> str | None:
        cmd = [binary, "audit", "system", "--cronjob", "--quiet"]

        def _run() -> subprocess.CompletedProcess[bytes]:
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            ) as proc:
                try:
                    stdout, stderr = proc.communicate(timeout=self._timeout_seconds)
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    try:
                        proc.communicate(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
                    raise
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=proc.returncode,
                stdout=stdout,
                stderr=stderr,
            )

        try:
            await asyncio.to_thread(_run)
        except subprocess.TimeoutExpired as exc:
            raise ProviderError(
                message=f"lynis timed out after {self._timeout_seconds}s",
                retryable=True,
            ) from exc
        except (FileNotFoundError, OSError):
            return None

        # lynis writes report to a predictable location
        for path in _REPORT_PATHS:
            if Path(path).exists():
                return path
        return None

    @staticmethod
    def _parse_report(report_path: str) -> dict[str, Any]:
        suggestions: list[str] = []
        warnings: list[str] = []
        hardening_index: int = 0
        os_name: str = ""

        try:
            with open(report_path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.rstrip()
                    if line.startswith(_SUGGESTION_PREFIX):
                        suggestions.append(line[len(_SUGGESTION_PREFIX) :])
                    elif line.startswith(_WARNING_PREFIX):
                        warnings.append(line[len(_WARNING_PREFIX) :])
                    elif line.startswith(_OS_KEY):
                        os_name = line[len(_OS_KEY) :]
                    elif line.startswith(_HARDENING_INDEX_KEY):
                        try:
                            hardening_index = int(line[len(_HARDENING_INDEX_KEY) :])
                        except ValueError:
                            pass
        except OSError:
            pass

        return {
            "hardening_index": hardening_index,
            "suggestions": suggestions,
            "warnings": warnings,
            "os": os_name,
            "raw_report_path": report_path,
        }
