# backend/app/providers/tools/holehe/client.py
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

_TOOL_NAME = "holehe"
_TIMEOUT_SECONDS = 30

_HOLEHE_WRAPPER = (
    "import holehe.core as c; " "c.check_update = lambda: None; " "c.main()"
)

# Strict email validation — must pass before being handed to subprocess.
# Rejects anything with shell-special characters regardless of quoting.
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import ProviderError


class HoleheProvider(BaseProviderClient):
    """Holehe - email-to-account enumeration tool wrapper.

    Runs ``holehe --only-used --no-color {email}`` and parses ``[+]`` lines
    to identify sites where the email address is registered.

    Requires holehe to be installed and available in PATH:
        pip install holehe
    """

    name = "tool_holehe"

    def __init__(self, timeout_seconds: int = 15) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    async def check_accounts_tool(self, email: str) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []

        email = email.strip()
        if not _EMAIL_RE.match(email):
            raise ProviderError(
                message=f"Invalid email address format: {email!r}",
                retryable=False,
            )
        invocation = self._resolve_invocation()
        found_sites = await self._run_holehe_async(email, invocation)

        for site in found_sites:
            findings.append(
                dict(
                    provider=self.name,
                    category="account_enumeration_risk",
                    title=f"Account found: {site}",
                    description=f"Email {email} is registered on {site}",
                    entity_type="email",
                    entity_value=email,
                    tags=["holehe", "account_enumeration", "email_registered"],
                    raw={
                        "site": site,
                        "email": email,
                    },
                )
            )

        return findings

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_invocation() -> list[str]:
        if importlib.util.find_spec(_TOOL_NAME) is not None:
            return [sys.executable, "-c", _HOLEHE_WRAPPER]

        binary = shutil.which(_TOOL_NAME)
        if binary:
            return [binary]

        raise ProviderError(
            message="holehe is not installed for the backend runtime. Install with: pip install holehe",
            retryable=False,
        )

    @staticmethod
    async def _run_holehe_async(email: str, invocation: list[str]) -> list[str]:
        """Run holehe in a thread pool with a hard blocking timeout.

        Uses asyncio.to_thread + subprocess.run instead of
        asyncio.create_subprocess_exec to avoid child-watcher issues in Docker
        environments where SIGCHLD delivery to the asyncio event loop is
        unreliable, which previously caused proc.wait() to hang indefinitely.
        """
        # "--" ends option processing so an email like "--help@x.com" is
        # treated as a positional argument, not a flag.
        cmd = [*invocation, "--only-used", "--no-color", "--", email]

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
                message=f"holehe timed out after {_TIMEOUT_SECONDS}s for {email}",
                retryable=True,
            ) from exc
        except FileNotFoundError as exc:
            raise ProviderError(
                message="holehe is not available to the backend runtime",
                retryable=False,
            ) from exc

        output = result.stdout.decode(errors="replace") + result.stderr.decode(
            errors="replace"
        )

        if result.returncode != 0:
            detail = " ".join(
                line.strip() for line in output.splitlines() if line.strip()
            )
            raise ProviderError(
                message=f"holehe failed for {email}: {detail[:400] or 'unknown error'}",
                retryable=False,
            )

        found: list[str] = []
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("[+]"):
                site = line[3:].strip().split(" / ", 1)[0].strip()
                if site:
                    found.append(site)
        return found
