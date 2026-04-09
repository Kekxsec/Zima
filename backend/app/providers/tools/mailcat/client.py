# backend/app/providers/tools/mailcat/client.py
"""Mailcat — Python CLI wrapper for discovering email addresses from a username."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import signal
import subprocess
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import ProviderError

_TOOL_NAME = "mailcat"
_TIMEOUT_SECONDS = 45

# Usernames: alphanumeric, dots, underscores, hyphens; 1–64 chars.
# Must start with alphanumeric to prevent flag injection.
_USERNAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._\-]{0,63}$")

# Match lines like: *  username@domain.tld  (sharsil/mailcat output format)
_FOUND_PATTERN = re.compile(r"^\*\s+(\S+@\S+\.\S+)")

_log = logging.getLogger(__name__)


class MailcatProvider(BaseProviderClient):
    """Mailcat - username-to-email discovery tool.

    Runs ``mailcat {username}`` and parses ``*`` lines to collect email
    addresses associated with the given username across known services.

    Requires mailcat (sharsil/mailcat) to be installed and in PATH.
    Output format: ``*  email@domain.com``
    """

    name = "tool_mailcat"

    def __init__(self, timeout_seconds: int = _TIMEOUT_SECONDS) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    async def find_emails(self, username: str) -> list[dict[str, Any]]:
        """Return findings for every email address discovered for *username*."""
        findings: list[dict[str, Any]] = []

        username = username.strip()
        if not _USERNAME_RE.match(username):
            raise ProviderError(
                message=f"Invalid username format: {username!r}",
                retryable=False,
            )

        binary = _resolve_binary()
        discovered = await _run_mailcat_async(username, binary)

        for email_addr in discovered:
            findings.append(
                dict(
                    provider=self.name,
                    category="account_inventory",
                    title=f"Email discovered: {email_addr}",
                    description=(
                        f"Username '{username}' is associated with {email_addr}"
                    ),
                    entity_type="username",
                    entity_value=username,
                    tags=["mailcat", "email_discovery", "account_inventory"],
                    raw={
                        "username": username,
                        "email": email_addr,
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
        message=(
            "mailcat is not installed. "
            "Install: pip install mailcat  (sharsil/mailcat)"
        ),
        retryable=False,
    )


async def _run_mailcat_async(username: str, binary: str) -> list[str]:
    """Run mailcat in a thread pool with a hard blocking timeout.

    stdout is parsed for results; stderr is logged at DEBUG and not mixed
    into the parsed output to avoid false-positive pattern matches.
    """
    cmd = [binary, "--", username]

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
                "mailcat stderr for %r: %s", username, stderr.decode(errors="replace")
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
            message=f"mailcat timed out after {_TIMEOUT_SECONDS}s for '{username}'",
            retryable=True,
        ) from exc
    except FileNotFoundError as exc:
        raise ProviderError(
            message="mailcat binary not found at runtime",
            retryable=False,
        ) from exc

    # Parse stdout only.
    found: list[str] = []
    for line in result.stdout.decode(errors="replace").splitlines():
        line = line.strip()
        match = _FOUND_PATTERN.match(line)
        if match:
            found.append(match.group(1).strip())
    return found
