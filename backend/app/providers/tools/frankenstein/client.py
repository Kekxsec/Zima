# backend/app/providers/tools/frankenstein/client.py
"""FRANKENSTEIN — dual-phenomenology DNS + HTTP/S site checker.

Runs the frankenstein binary against a list of domains and parses the
SQLite output to extract TLS certificate data, security headers, HTTP
metadata, and domain status (ALIVE / DNS-ONLY / DEAD).

Source: https://github.com/Ringmast4r/FRANKENSTEIN
Install: go build from source, place binary in PATH as 'frankenstein'

The provider writes a temporary input file, invokes the binary, reads the
SQLite output, and returns normalised per-domain result dicts.  The module
(infrastructure_exposure or browser_configuration) is responsible for
severity assignment.
"""

from __future__ import annotations

import asyncio
import os
import shutil
import signal
import sqlite3
import subprocess
import tempfile
from datetime import UTC, datetime
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import ProviderError

_TOOL_NAME = "frankenstein"
_TIMEOUT_SECONDS = 120  # Batch runs may take longer than single-domain checks
_STATUS_ALIVE = "ALIVE"
_STATUS_DNS_ONLY = "DNS-ONLY"
_STATUS_DEAD = "DEAD"


class FrankensteinProvider(BaseProviderClient):
    """FRANKENSTEIN domain posture checker.

    Probes a list of domains for:
    - DNS resolution (A/AAAA/CNAME/MX/NS records)
    - HTTP/S availability and security headers
    - TLS certificate validity (expiry, self-signed)
    - Domain status classification: ALIVE / DNS-ONLY / DEAD

    Requires the frankenstein binary compiled and available in PATH.
    """

    name = "frankenstein"

    def __init__(self, timeout_seconds: int = _TIMEOUT_SECONDS) -> None:
        super().__init__(timeout_seconds=timeout_seconds)

    async def probe_domains(self, domains: list[str]) -> list[dict[str, Any]]:
        """Probe *domains* and return a normalised result dict per domain.

        Each result dict contains TLS, HTTP, DNS, and security header fields.
        Returns an empty list if the binary is unavailable.
        """
        if not domains:
            return []

        binary = self._resolve_binary()

        with tempfile.TemporaryDirectory() as tmp_dir:
            input_file = os.path.join(tmp_dir, "domains.txt")
            output_db = os.path.join(tmp_dir, "results.db")

            with open(input_file, "w") as f:
                for domain in domains:
                    domain = domain.strip()
                    if domain:
                        f.write(domain + "\n")

            await self._run_frankenstein(binary, input_file, output_db)

            if not os.path.exists(output_db):
                raise ProviderError(
                    message="frankenstein produced no output database",
                    retryable=False,
                )

            return self._parse_output(output_db)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_binary() -> str:
        binary = shutil.which(_TOOL_NAME)
        if not binary:
            raise ProviderError(
                message=(
                    "frankenstein binary not found in PATH. "
                    "Build from source: https://github.com/Ringmast4r/FRANKENSTEIN"
                ),
                retryable=False,
            )
        return binary

    async def _run_frankenstein(
        self, binary: str, input_file: str, output_db: str
    ) -> None:
        """Invoke the frankenstein binary as a subprocess."""
        cmd = [binary, "-input", input_file, "-output", output_db]

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
                message=f"frankenstein timed out after {self._timeout_seconds}s",
                retryable=True,
            ) from exc
        except FileNotFoundError as exc:
            raise ProviderError(
                message="frankenstein binary not available",
                retryable=False,
            ) from exc

        if result.returncode != 0:
            stderr_text = result.stderr.decode(errors="replace")[:400]
            raise ProviderError(
                message=f"frankenstein exited with code {result.returncode}: {stderr_text}",
                retryable=False,
            )

    @staticmethod
    def _parse_output(db_path: str) -> list[dict[str, Any]]:
        """Read the SQLite results database and return normalised dicts."""
        results: list[dict[str, Any]] = []

        try:
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            try:
                cursor = conn.execute("SELECT * FROM results")
                rows = cursor.fetchall()
            finally:
                conn.close()
        except sqlite3.Error as exc:
            raise ProviderError(
                message=f"frankenstein output DB read failed: {exc}",
                retryable=False,
            ) from exc

        now = datetime.now(UTC)

        for row in rows:
            d: dict[str, Any] = dict(row)
            results.append(FrankensteinProvider._normalise_row(d, now))

        return results

    @staticmethod
    def _normalise_row(row: dict[str, Any], now: datetime) -> dict[str, Any]:
        """Normalise a single SQLite row into the provider finding contract."""
        domain: str = str(row.get("domain") or "")
        status: str = str(row.get("status") or "").upper()
        tls_expiry_raw: str | None = row.get("tls_expiry")

        # Parse TLS expiry
        tls_expiry: datetime | None = None
        if tls_expiry_raw:
            for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    tls_expiry = datetime.strptime(tls_expiry_raw, fmt).replace(
                        tzinfo=UTC
                    )
                    break
                except ValueError:
                    continue

        # Compute derived TLS state
        tls_expired = tls_expiry is not None and tls_expiry < now
        days_until_expiry: int | None = None
        if tls_expiry and not tls_expired:
            days_until_expiry = (tls_expiry - now).days

        # Parse security header booleans — SQLite stores as int 0/1
        def _bool(key: str) -> bool:
            val = row.get(key)
            if val is None:
                return False
            return bool(int(val)) if isinstance(val, int | float) else bool(val)

        # Build the missing headers list for the module
        missing_headers: list[str] = []
        if not _bool("hsts"):
            missing_headers.append("Strict-Transport-Security")
        if not row.get("x_frame_options"):
            missing_headers.append("X-Frame-Options")
        if not row.get("cache_control"):
            missing_headers.append("Cache-Control")

        return {
            "provider": "frankenstein",
            "category": "infrastructure_security",
            "entity_type": "domain",
            "entity_value": domain,
            # Domain health
            "domain": domain,
            "status": status,
            "is_alive": status == _STATUS_ALIVE,
            "is_dns_only": status == _STATUS_DNS_ONLY,
            "is_dead": status == _STATUS_DEAD,
            # DNS
            "dns_a": _split_csv(row.get("dns_a")),
            "dns_cname": str(row.get("dns_cname") or ""),
            "dns_mx": _split_csv(row.get("dns_mx")),
            "dns_ns": _split_csv(row.get("dns_ns")),
            # HTTP
            "http_status": _int_or_none(row.get("http_status")),
            "http_title": str(row.get("http_title") or ""),
            "http_server": str(row.get("http_server") or ""),
            "http_redirect_chain": _split_csv(row.get("http_redirect_chain")),
            # TLS
            "tls_issuer": str(row.get("tls_issuer") or ""),
            "tls_cn": str(row.get("tls_cn") or ""),
            "tls_expiry": tls_expiry.isoformat() if tls_expiry else None,
            "tls_expired": tls_expired,
            "tls_self_signed": _bool("tls_self_signed"),
            "days_until_expiry": days_until_expiry,
            # Security headers
            "hsts": _bool("hsts"),
            "x_frame_options": str(row.get("x_frame_options") or ""),
            "cache_control": str(row.get("cache_control") or ""),
            "missing_security_headers": missing_headers,
            # Performance
            "response_time_ms": _int_or_none(row.get("response_time_ms")),
            "raw": dict(row),
        }


def _split_csv(value: Any) -> list[str]:
    """Split a comma-separated string from SQLite into a list."""
    if not value:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    text = str(value).strip()
    if not text:
        return []
    return [part.strip() for part in text.split(",") if part.strip()]


def _int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
