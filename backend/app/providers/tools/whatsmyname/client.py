# backend/app/providers/tools/whatsmyname/client.py
"""WhatsmyName — username enumeration across 500+ sites (CLI wrapper)."""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import signal
import subprocess
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import ProviderError

_TOOL_NAME = "whatsmyname"
_TIMEOUT_SECONDS = 60

# Usernames: alphanumeric, dots, underscores, hyphens; 1–64 chars.
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._\-]{0,63}$")

# Match lines like: [+] SiteName - https://site.com/username
# WhatsmyName outputs: [+] Twitter - https://twitter.com/user
_FOUND_PATTERN = re.compile(r"^\[\+\]\s+(.+?)\s+-\s+(https?://\S+)", re.IGNORECASE)


class WhatsmyNameProvider(BaseProviderClient):
    """WhatsmyName - username-to-account enumeration across 500+ sites.

    Runs ``whatsmyname -u {username}`` and parses ``[+]`` output lines
    to discover accounts registered under the given username.

    Requires whatsmyname to be installed and in PATH:
        pip install whatsmyname
        # or: git clone https://github.com/WebBreacher/WhatsMyName
    """

    name = "tool_whatsmyname"

    def __init__(self, timeout_seconds: int = _TIMEOUT_SECONDS) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    async def search_username(self, username: str) -> list[dict[str, Any]]:
        """Return findings for every account found for *username*."""
        findings: list[dict[str, Any]] = []

        username = username.strip()
        if not _USERNAME_RE.match(username):
            raise ProviderError(
                message=f"Invalid username format: {username!r}",
                retryable=False,
            )

        binary = _resolve_binary()
        discovered = await _run_whatsmyname_async(username, binary)

        for site_name, url in discovered:
            findings.append(
                dict(
                    provider=self.name,
                    category="username_exposure",
                    title=f"Username found: {site_name}",
                    description=f"Username '{username}' found on {site_name}: {url}",
                    entity_type="username",
                    entity_value=username,
                    tags=["whatsmyname", "username_enum", "account_discovery"],
                    raw={
                        "site": site_name,
                        "url": url,
                        "username": username,
                    },
                )
            )

        return findings


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_binary() -> str:
    binary = shutil.which(_TOOL_NAME)
    if binary:
        return binary
    raise ProviderError(
        message=("whatsmyname is not installed. " "Install: pip install whatsmyname"),
        retryable=False,
    )


async def _run_whatsmyname_async(username: str, binary: str) -> list[tuple[str, str]]:
    """Run whatsmyname in a thread pool with a hard blocking timeout."""
    cmd = [binary, "-u", username]

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
            message=f"whatsmyname timed out after {_TIMEOUT_SECONDS}s for '{username}'",
            retryable=True,
        ) from exc
    except FileNotFoundError as exc:
        raise ProviderError(
            message="whatsmyname binary not found at runtime",
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
