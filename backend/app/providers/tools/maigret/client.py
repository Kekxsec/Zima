# backend/app/providers/tools/maigret/client.py
from __future__ import annotations

import asyncio
import importlib.util
import os
import re
import shutil
import signal
import subprocess
import sys
from typing import Any

_TOOL_NAME = "maigret"
_TIMEOUT_SECONDS = 45

# Matches lines like: [+] SiteName: https://site.com/username
_FOUND_PATTERN = re.compile(r"^\[\+\]\s+(.+?):\s+(https?://\S+)", re.IGNORECASE)

# Usernames: alphanumeric, dots, underscores, hyphens; 1–64 chars.
# Rejects leading hyphens (which would be parsed as flags) and shell metacharacters.
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._\-]{0,63}$")


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class MaigretProvider(BaseProviderClient):
    """Maigret - username profiling across 3000+ sites.

    Runs ``maigret {username} --no-color -a --timeout 10 --no-progressbar``
    and parses ``[+]`` lines to discover accounts linked to the username.

    Requires maigret to be installed and available in PATH:
        pip install maigret
    """

    name = "tool_maigret"

    def __init__(self, timeout_seconds: int = 15) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    async def search_usernames(self, username: str) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []

        username = username.strip()
        if not _USERNAME_RE.match(username):
            raise ProviderError(
                message=f"Invalid username format: {username!r}",
                retryable=False,
            )
        invocation = self._resolve_invocation()
        found_accounts = await self._run_maigret_async(username, invocation)

        for site_name, url in found_accounts:
            findings.append(
                dict(
                    provider=self.name,
                    category="username_exposure",
                    title=f"Username found: {site_name}",
                    description=f"Username {username} found on {site_name}: {url}",
                    entity_type="username",
                    entity_value=username,
                    tags=["maigret", "username_enum", "account_discovery"],
                    raw={
                        "site": site_name,
                        "url": url,
                        "username": username,
                    },
                )
            )

        return findings

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_invocation() -> list[str]:
        binary = shutil.which(_TOOL_NAME)
        if binary:
            return [binary]

        if importlib.util.find_spec(_TOOL_NAME) is not None:
            return [sys.executable, "-m", _TOOL_NAME]

        raise ProviderError(
            message="maigret is not installed for the backend runtime. Install with: pip install maigret",
            retryable=False,
        )

    @staticmethod
    async def _run_maigret_async(
        username: str, invocation: list[str]
    ) -> list[tuple[str, str]]:
        """Run maigret in a thread pool with a hard blocking timeout.

        Uses asyncio.to_thread + subprocess.run instead of
        asyncio.create_subprocess_exec to avoid child-watcher issues in Docker
        environments where SIGCHLD delivery to the asyncio event loop is
        unreliable, which previously caused proc.wait() to hang indefinitely.
        """
        cmd = [
            *invocation,
            username,
            "--no-color",
            "-a",
            "--timeout",
            "5",
            "--no-progressbar",
        ]

        def _run() -> subprocess.CompletedProcess[bytes]:
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
            ) as proc:
                try:
                    stdout, stderr = proc.communicate(timeout=_TIMEOUT_SECONDS)
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
                message=(
                    f"maigret timed out after {_TIMEOUT_SECONDS}s for username "
                    f"'{username}'"
                ),
                retryable=True,
            ) from exc
        except FileNotFoundError as exc:
            raise ProviderError(
                message="maigret is not available to the backend runtime",
                retryable=False,
            ) from exc

        output = result.stdout.decode(errors="replace") + result.stderr.decode(
            errors="replace"
        )
        found: list[tuple[str, str]] = []
        for line in output.splitlines():
            line = line.strip()
            match = _FOUND_PATTERN.match(line)
            if match:
                site_name = match.group(1).strip()
                url = match.group(2).strip()
                found.append((site_name, url))
        return found
