# backend/app/providers/tools/trivy/client.py
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

_TOOL_NAME = "trivy"
_TIMEOUT_SECONDS = 180


class TrivyProvider(BaseProviderClient):
    """Trivy — vulnerability scanner for filesystems and container images.

    Runs ``trivy fs --format json --quiet {target}`` and returns parsed
    vulnerability findings. Also supports container image scanning.

    Requires trivy to be installed:
        https://aquasecurity.github.io/trivy/latest/getting-started/installation/
    """

    name = "trivy"

    def __init__(self, timeout_seconds: int = _TIMEOUT_SECONDS) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    async def scan_filesystem(self, target: str = "/") -> list[dict[str, Any]]:
        """Scan a local filesystem path for vulnerabilities.

        Returns list of vulnerability finding dicts with keys:
          target, vuln_id, pkg_name, installed_version, fixed_version,
          severity, title, description, references.
        """
        target = target.strip() or "/"
        binary = self._resolve_binary()
        raw = await self._run_scan(binary, ["fs", target])
        return self._parse_results(raw)

    async def scan_image(self, image: str) -> list[dict[str, Any]]:
        """Scan a container image for vulnerabilities."""
        if not image.strip():
            raise ProviderError(
                message="Trivy image target must not be empty", retryable=False
            )
        binary = self._resolve_binary()
        raw = await self._run_scan(binary, ["image", image.strip()])
        return self._parse_results(raw)

    @staticmethod
    def _resolve_binary() -> str:
        binary = shutil.which(_TOOL_NAME)
        if not binary:
            raise ProviderError(
                message=(
                    "trivy is not installed or not in PATH. "
                    "Install: https://aquasecurity.github.io/trivy/"
                ),
                retryable=False,
            )
        return binary

    async def _run_scan(self, binary: str, extra_args: list[str]) -> str:
        cmd = [binary, *extra_args, "--format", "json", "--quiet"]

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
                message=f"trivy timed out after {self._timeout_seconds}s",
                retryable=True,
            ) from exc
        except FileNotFoundError as exc:
            raise ProviderError(
                message="trivy binary not found", retryable=False
            ) from exc

        if result.returncode not in (0, 1):
            stderr_text = result.stderr.decode(errors="replace")[:300]
            raise ProviderError(
                message=f"trivy exited with code {result.returncode}: {stderr_text}",
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
        results = data.get("Results", [])
        if not isinstance(results, list):
            return []

        for result in results:
            target = result.get("Target", "")
            vulnerabilities = result.get("Vulnerabilities") or []
            for vuln in vulnerabilities:
                if not isinstance(vuln, dict):
                    continue
                findings.append(
                    {
                        "target": target,
                        "vuln_id": vuln.get("VulnerabilityID", ""),
                        "pkg_name": vuln.get("PkgName", ""),
                        "installed_version": vuln.get("InstalledVersion", ""),
                        "fixed_version": vuln.get("FixedVersion", ""),
                        "severity": vuln.get("Severity", "UNKNOWN").upper(),
                        "title": vuln.get("Title", ""),
                        "description": vuln.get("Description", "")[:500],
                        "references": vuln.get("References", [])[:5],
                        "cvss": vuln.get("CVSS", {}),
                    }
                )

        return findings
