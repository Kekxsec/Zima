# backend/app/providers/tools/syft/client.py
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

_TOOL_NAME = "syft"
_TIMEOUT_SECONDS = 120


class SyftProvider(BaseProviderClient):
    """Syft — software bill of materials (SBOM) scanner.

    Runs ``syft {target} -o json`` as a subprocess and returns the parsed
    JSON output. Target can be a local path (e.g. "/" or "dir:/path"),
    a container image (e.g. "docker:image:tag"), or any target Syft supports.

    Requires syft to be installed and available in PATH:
        curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh
    """

    name = "syft"

    def __init__(self, timeout_seconds: int = _TIMEOUT_SECONDS) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    async def scan(self, target: str, output_format: str = "json") -> dict[str, Any]:
        """Run Syft against target and return parsed JSON output.

        Returns the full Syft JSON document (keys: artifacts, source, distro,
        schema, descriptor). Raises ProviderError on timeout or if syft is not
        installed.
        """
        target = target.strip()
        if not target:
            raise ProviderError(
                message="Syft scan target must not be empty", retryable=False
            )

        invocation = self._resolve_invocation()
        raw_output = await self._run_syft_async(target, invocation, output_format)

        try:
            return json.loads(raw_output)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ProviderError(
                message="Syft output could not be parsed as JSON", retryable=False
            ) from exc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_invocation() -> list[str]:
        binary = shutil.which(_TOOL_NAME)
        if binary:
            return [binary]
        raise ProviderError(
            message=(
                "syft is not installed or not in PATH. "
                "Install: curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh"
            ),
            retryable=False,
        )

    async def _run_syft_async(
        self, target: str, invocation: list[str], output_format: str
    ) -> str:
        cmd = [*invocation, target, "-o", output_format, "--quiet"]

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
                message=f"syft timed out after {self._timeout_seconds}s for target '{target}'",
                retryable=True,
            ) from exc
        except FileNotFoundError as exc:
            raise ProviderError(
                message="syft binary not found", retryable=False
            ) from exc

        if result.returncode != 0:
            stderr_text = result.stderr.decode(errors="replace")[:500]
            raise ProviderError(
                message=f"syft exited with code {result.returncode}: {stderr_text}",
                retryable=False,
            )

        return result.stdout.decode(errors="replace")
