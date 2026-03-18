# backend/app/providers/tools/holehe/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.LOW
# --- End migration notes ---
import shutil
import subprocess
from typing import Any

_TOOL_NAME = "holehe"
_TIMEOUT_SECONDS = 120


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class HoleheProvider(BaseProviderClient):
    """Holehe - email-to-account enumeration tool wrapper.

    Runs ``holehe --only-used --no-color {email}`` and parses ``[+]`` lines
    to identify sites where the email address is registered.

    Requires holehe to be installed and available in PATH:
        pip install holehe
    """

    name = "tool_holehe"

    async def check_accounts_tool(self, email: str) -> list[dict[str, Any]]:
        if not shutil.which(_TOOL_NAME):
            raise ProviderError(
                message="holehe not found in PATH, install with: pip install holehe",
                retryable=False,
            )

        findings: list = []
        evidence: list = []

        email = email.strip()
        found_sites = self._run_holehe(email)

        for site in found_sites:
            findings.append(
                dict(
                    provider=self.name,
                    category="account_enumeration_risk",
                    title=f"Account found: {site}",
                    description=f"Email {email} is registered on {site}",
                    entity_type="email",
                    entity_value=email,
                    confidence=0.75,
                    tags=["holehe", "account_enumeration", "email_registered"],
                )
            )

        if found_sites:
            evidence.append(
                dict(
                    source=self.name,
                    description=f"Holehe account enumeration results for {email}",
                    raw={
                        "email": email,
                        "sites_found": found_sites,
                        "count": len(found_sites),
                    },
                    confidence=0.75,
                )
            )

        return findings

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _run_holehe(email: str) -> list[str]:
        """Run holehe and return a list of site names where the email is found."""
        cmd = [_TOOL_NAME, "--only-used", "--no-color", email]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderError(
                message=f"holehe timed out after {_TIMEOUT_SECONDS}s for {email}",
                retryable=True,
            ) from exc
        except FileNotFoundError as exc:
            raise ProviderError(
                message="holehe not found in PATH, install with: pip install holehe",
                retryable=False,
            ) from exc

        output = result.stdout + result.stderr
        found: list[str] = []
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("[+]"):
                site = line[3:].strip()
                if site:
                    found.append(site)
        return found
