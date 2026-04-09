# backend/app/providers/tools/whatsmyname/client.py
"""Sherlock — username enumeration across 400+ sites (CLI wrapper).

Provider name kept as ``tool_whatsmyname`` for stable identifier compatibility.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import signal
import subprocess
import tempfile
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import ProviderError

_TOOL_NAME = "sherlock"
_TIMEOUT_SECONDS = 90

# Usernames: alphanumeric, dots, underscores, hyphens; 1–64 chars.
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._\-]{0,63}$")

# Strip ANSI escape codes (all CSI sequences, not just SGR).
_ANSI_RE = re.compile(r"\x1b\[[^@-~]*[@-~]")

# Match lines like: [+] SiteName: https://site.com/username
_FOUND_PATTERN = re.compile(r"^\[\+\]\s+(.+?):\s+(https?://\S+)", re.IGNORECASE)

_log = logging.getLogger(__name__)


class WhatsmyNameProvider(BaseProviderClient):
    """Sherlock - username enumeration across 400+ sites.

    Runs ``sherlock --print-found {username}`` and parses ``[+]`` output
    lines to discover accounts registered under the given username.

    Provider name is ``tool_whatsmyname`` for backward compatibility.

    Requires sherlock to be installed and in PATH:
        pip install sherlock-project
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
        discovered = await _run_sherlock_async(username, binary)

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
        message=("sherlock is not installed. " "Install: pip install sherlock-project"),
        retryable=False,
    )


async def _run_sherlock_async(username: str, binary: str) -> list[tuple[str, str]]:
    """Run sherlock in a thread pool with a hard blocking timeout.

    Sherlock writes ``{username}.txt`` to its working directory by default.
    We run it inside a TemporaryDirectory so the file is isolated and
    automatically cleaned up — no scan artefacts land in the repo root or
    any other persistent path.
    """

    def _run() -> subprocess.CompletedProcess[bytes]:
        # cwd=tmpdir keeps sherlock's output file out of the repo root.
        with tempfile.TemporaryDirectory(prefix="zima_sherlock_") as tmpdir:
            cmd = [binary, "--print-found", username]
            with subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=True,
                cwd=tmpdir,
            ) as proc:
                try:
                    stdout, stderr = proc.communicate(timeout=_TIMEOUT_SECONDS)
                except subprocess.TimeoutExpired:
                    # SIGTERM first, then SIGKILL after a short grace period.
                    try:
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    except ProcessLookupError:
                        pass
                    try:
                        proc.communicate(timeout=2)
                    except subprocess.TimeoutExpired:
                        try:
                            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                        proc.communicate(timeout=5)
                    raise
            if stderr:
                _log.debug(
                    "sherlock stderr for %r: %s",
                    username,
                    stderr.decode(errors="replace"),
                )
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=proc.returncode,
            stdout=stdout,
            stderr=b"",
        )

    try:
        result = await asyncio.to_thread(_run)
    except subprocess.TimeoutExpired as exc:
        raise ProviderError(
            message=f"sherlock timed out after {_TIMEOUT_SECONDS}s for '{username}'",
            retryable=True,
        ) from exc
    except FileNotFoundError as exc:
        raise ProviderError(
            message="sherlock binary not found at runtime",
            retryable=False,
        ) from exc

    # Parse stdout only; stderr was already logged separately above.
    output = _ANSI_RE.sub("", result.stdout.decode(errors="replace"))

    found: list[tuple[str, str]] = []
    for line in output.splitlines():
        line = line.strip()
        match = _FOUND_PATTERN.match(line)
        if match:
            site_name = match.group(1).strip()
            url = match.group(2).strip()
            found.append((site_name, url))
    return found
