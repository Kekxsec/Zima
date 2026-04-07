# backend/app/providers/tools/grype/client.py
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

_TOOL_NAME = "grype"
_TIMEOUT_SECONDS = 180


class GrypeProvider(BaseProviderClient):
    """Grype — vulnerability scanner for SBOMs and container images.

    Runs ``grype {target} -o json --quiet`` and returns parsed CVE findings.
    Works against filesystem paths, container images, or Syft SBOM files.

    Requires grype to be installed:
        https://github.com/anchore/grype
    """

    name = "grype"

    def __init__(self, timeout_seconds: int = _TIMEOUT_SECONDS) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    async def scan(self, target: str) -> list[dict[str, Any]]:
        """Scan target for vulnerabilities.

        target: e.g. "/", "dir:/path", "docker:image:tag", "sbom:path/to/sbom.json"

        Returns list of vulnerability finding dicts with keys:
          vuln_id, pkg_name, installed_version, fixed_version,
          severity, description, data_source, namespace.
        """
        target = target.strip()
        if not target:
            raise ProviderError(
                message="Grype scan target must not be empty", retryable=False
            )

        binary = shutil.which(_TOOL_NAME)
        if not binary:
            raise ProviderError(
                message=(
                    "grype is not installed or not in PATH. "
                    "Install: curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh"
                ),
                retryable=False,
            )

        raw = await self._run_scan(binary, target)
        return self._parse_results(raw)

    async def _run_scan(self, binary: str, target: str) -> str:
        cmd = [binary, target, "-o", "json", "--quiet"]

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
                message=f"grype timed out after {self._timeout_seconds}s for target '{target}'",
                retryable=True,
            ) from exc
        except FileNotFoundError as exc:
            raise ProviderError(
                message="grype binary not found", retryable=False
            ) from exc

        if result.returncode not in (0, 1):
            stderr_text = result.stderr.decode(errors="replace")[:300]
            raise ProviderError(
                message=f"grype exited with code {result.returncode}: {stderr_text}",
                retryable=False,
            )

        return result.stdout.decode(errors="replace")

    @staticmethod
    def _parse_results(raw: str) -> list[dict[str, Any]]:
        if not raw.strip():
            return []
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return []

        findings: list[dict[str, Any]] = []
        matches = data.get("matches", [])
        if not isinstance(matches, list):
            return []

        for match in matches:
            if not isinstance(match, dict):
                continue
            vuln = match.get("vulnerability", {})
            artifact = match.get("artifact", {})
            findings.append(
                {
                    "vuln_id": vuln.get("id", ""),
                    "pkg_name": artifact.get("name", ""),
                    "pkg_version": artifact.get("version", ""),
                    "pkg_type": artifact.get("type", ""),
                    "pkg_location": (artifact.get("locations") or [{}])[0].get(
                        "realPath", ""
                    ),
                    "fixed_version": (vuln.get("fix", {}).get("versions") or [""])[0],
                    "severity": vuln.get("severity", "Unknown").upper(),
                    "description": vuln.get("description", "")[:500],
                    "data_source": vuln.get("dataSource", ""),
                    "namespace": vuln.get("namespace", ""),
                    "cvss": vuln.get("cvss", []),
                }
            )

        return findings
