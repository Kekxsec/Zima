# backend/app/providers/domain/sslcert/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_sslcert.py (MIT licensed)
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class SslcertProvider(BaseProviderClient):
    name = "sslcert"
    # Uses crt.sh API to get certificate info
    base_url = "https://crt.sh"

    def __init__(self, timeout_seconds: int = 15):
        self._timeout_seconds = timeout_seconds

    async def get_certificates(self, domain: str) -> list[dict[str, Any]]:
        findings, evidence = [], []
        seen: set[str] = set()
        val = domain.strip()
        url = f"{self.base_url}/?{urllib.parse.urlencode({'q': val, 'output': 'json'})}"
        data = self._fetch(url)
        certs = data if isinstance(data, list) else []
        if not isinstance(certs, list):
            return findings
        for cert in certs[:20]:
            if not isinstance(cert, dict):
                continue
            name_value = str(cert.get("name_value", "")).strip()
            issuer = str(cert.get("issuer_name", "")).strip()
            str(cert.get("entry_timestamp", "")).strip()
            if not name_value or name_value in seen:
                continue
            seen.add(name_value)
            for cn in name_value.splitlines():
                cn = cn.strip()
                if cn and cn not in seen:
                    seen.add(cn)
                    findings.append(
                        dict(
                            provider=self.name,
                            category="ssl_certificate",
                            title=f"SSL cert: {cn}",
                            description=f"SSL certificate for {val}: CN={cn}"
                            + (f", issuer={issuer[:50]}" if issuer else ""),
                            entity_type="hostname",
                            entity_value=cn,
                            confidence=0.85,
                            tags=["sslcert", "ssl", "passive"],
                        )
                    )
            if certs:
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"SSL certificates for {val}",
                        raw={"count": len(certs)},
                        confidence=0.85,
                    )
                )
        return findings

    async def _fetch(self, url: str) -> list:
        return await self._get(url, label="Sslcert", timeout=self._timeout_seconds)
