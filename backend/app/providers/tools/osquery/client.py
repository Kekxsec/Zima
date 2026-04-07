# backend/app/providers/tools/osquery/client.py
from __future__ import annotations

import asyncio
import json
import os
import shutil
import signal
import subprocess
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import ProviderError

_TOOL_NAME = "osqueryi"
_TIMEOUT_SECONDS = 30

# Pre-defined queries used by device modules.
QUERIES: dict[str, str] = {
    "os_version": "SELECT name, version, major, minor, patch, build FROM os_version LIMIT 1;",
    "kernel_info": "SELECT version, arguments FROM kernel_info LIMIT 1;",
    "patches": "SELECT hotfix_id, installed_on FROM patches;",
    "interface_details": "SELECT interface, mac, type FROM interface_details WHERE mac != '' AND mac != '00:00:00:00:00:00';",
    "iptables": "SELECT filter_name, chain, policy, target, src_ip, dst_ip FROM iptables LIMIT 200;",
    "processes": "SELECT pid, name, path, uid FROM processes LIMIT 500;",
    "users": "SELECT uid, gid, username, directory, shell FROM users;",
    "listening_ports": "SELECT pid, port, protocol, address FROM listening_ports;",
    "startup_items": "SELECT name, type, path, source FROM startup_items;",
    "launchd": "SELECT label, program, run_at_load, disabled FROM launchd LIMIT 200;",
}


class OsqueryProvider(BaseProviderClient):
    """Osquery — universal OS telemetry via SQL queries.

    Runs ``osqueryi -S --json "{sql}"`` as a subprocess and returns the
    parsed JSON result rows.

    Requires osquery to be installed:
        https://osquery.io/downloads/official/
    """

    name = "osquery"

    def __init__(self, timeout_seconds: int = _TIMEOUT_SECONDS) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    async def query(self, sql: str) -> list[dict[str, Any]]:
        """Run an osquery SQL statement and return result rows.

        Returns an empty list if osquery is not installed or if the query
        returns no results. Raises ProviderError on hard failures.
        """
        sql = sql.strip()
        if not sql:
            raise ProviderError(
                message="osquery SQL must not be empty", retryable=False
            )

        binary = shutil.which(_TOOL_NAME)
        if not binary:
            raise ProviderError(
                message=(
                    "osqueryi is not installed or not in PATH. "
                    "Install: https://osquery.io/downloads/"
                ),
                retryable=False,
            )

        return await self._run_query(binary, sql)

    async def query_named(self, name: str) -> list[dict[str, Any]]:
        """Run a pre-defined query by name (see QUERIES dict).

        Returns [] if the query name is unknown or osquery is not available.
        """
        sql = QUERIES.get(name)
        if not sql:
            raise ProviderError(
                message=f"Unknown osquery preset: {name!r}", retryable=False
            )
        return await self.query(sql)

    async def _run_query(self, binary: str, sql: str) -> list[dict[str, Any]]:
        cmd = [binary, "--json", sql]

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
            result = await asyncio.to_thread(_run)
        except subprocess.TimeoutExpired as exc:
            raise ProviderError(
                message=f"osqueryi timed out after {self._timeout_seconds}s",
                retryable=True,
            ) from exc
        except FileNotFoundError as exc:
            raise ProviderError(
                message="osqueryi binary not found", retryable=False
            ) from exc

        if result.returncode not in (0, 1):
            stderr_text = result.stderr.decode(errors="replace")[:300]
            raise ProviderError(
                message=f"osqueryi exited with code {result.returncode}: {stderr_text}",
                retryable=False,
            )

        stdout_text = result.stdout.decode(errors="replace").strip()
        if not stdout_text:
            return []

        try:
            rows = json.loads(stdout_text)
            return rows if isinstance(rows, list) else []
        except (json.JSONDecodeError, ValueError):
            return []
