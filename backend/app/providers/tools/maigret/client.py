# backend/app/providers/tools/maigret/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.LOW
# --- End migration notes ---
import re
import shutil
import subprocess
from typing import Any

_TOOL_NAME = "maigret"
_TIMEOUT_SECONDS = 180

# Matches lines like: [+] SiteName: https://site.com/username
_FOUND_PATTERN = re.compile(r"^\[\+\]\s+(.+?):\s+(https?://\S+)", re.IGNORECASE)


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class MaigretProvider(BaseProviderClient):
    """Maigret - username profiling across 3000+ sites.

    Runs ``maigret {username} --no-color -a --timeout 10 --print-found``
    and parses ``[+]`` lines to discover accounts linked to the username.

    Requires maigret to be installed and available in PATH:
        pip install maigret
    """

    name = "tool_maigret"

    async def search_usernames(self, username: str) -> list[dict[str, Any]]:
        if not shutil.which(_TOOL_NAME):
            raise ProviderError(
                message="maigret not found in PATH, install with: pip install maigret",
                retryable=False,
            )

        findings: list = []
        evidence: list = []

        username = username.strip()
        found_accounts = self._run_maigret(username)

        for site_name, url in found_accounts:
            findings.append(
                dict(
                    provider=self.name,
                    category="username_exposure",
                    title=f"Username found: {site_name}",
                    description=f"Username {username} found on {site_name}: {url}",
                    entity_type="username",
                    entity_value=username,
                    confidence=0.70,
                    tags=["maigret", "username_enum", "account_discovery"],
                )
            )

        if found_accounts:
            evidence.append(
                dict(
                    source=self.name,
                    description=f"Maigret username enumeration results for {username}",
                    raw={
                        "username": username,
                        "count": len(found_accounts),
                        "sites": [{"site": s, "url": u} for s, u in found_accounts],
                    },
                    confidence=0.70,
                )
            )

        return findings

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _run_maigret(username: str) -> list[tuple[str, str]]:
        """Run maigret and return a list of (site_name, url) tuples."""
        cmd = [
            _TOOL_NAME,
            username,
            "--no-color",
            "-a",
            "--timeout",
            "10",
            "--print-found",
        ]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderError(
                message=f"maigret timed out after {_TIMEOUT_SECONDS}s for username '{username}'",
                retryable=True,
            ) from exc
        except FileNotFoundError as exc:
            raise ProviderError(
                message="maigret not found in PATH, install with: pip install maigret",
                retryable=False,
            ) from exc

        output = result.stdout + result.stderr
        found: list[tuple[str, str]] = []
        for line in output.splitlines():
            line = line.strip()
            match = _FOUND_PATTERN.match(line)
            if match:
                site_name = match.group(1).strip()
                url = match.group(2).strip()
                found.append((site_name, url))
        return found
