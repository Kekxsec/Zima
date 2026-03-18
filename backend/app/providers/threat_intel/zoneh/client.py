# backend/app/providers/threat_intel/zoneh/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.HIGH
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_zoneh.py (MIT licensed)
import re
import urllib.parse
from typing import Any

DEFACEMENT_RE = re.compile(
    r'<td[^>]*>\s*<a[^>]+href="(/mirror/[^"]+)"[^>]*>([^<]+)</a>', re.IGNORECASE
)


from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class ZonehProvider(BaseProviderClient):
    name = "zoneh"
    base_url = "https://www.zone-h.org"

    def __init__(self, timeout_seconds: int = 20):
        self._timeout_seconds = timeout_seconds

    async def check_defacement(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        findings, evidence = [], []
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            if _entity_type not in {"domain", "ip_address"}:
                continue
            val = _value.strip()
            urllib.parse.urlencode({"domain": val, "hz": "1"})
            url = f"{self.base_url}/archive/filter=domain/domain={urllib.parse.quote(val)}"
            try:
                resp = await self._get(url, timeout=self._timeout_seconds)
            except Exception as exc:
                raise ProviderError(
                    message="Zone-H request failed", retryable=True
                ) from exc
            if resp.status_code == 429:
                raise ProviderError(message="Zone-H rate limited", retryable=True)
            if resp.status_code != 200:
                continue
            content = (
                resp.content
                if isinstance(resp.content, str)
                else resp.content.decode("utf-8", errors="replace")
            )
            matches = DEFACEMENT_RE.findall(content)
            if matches:
                findings.append(
                    dict(
                        provider=self.name,
                        category="defacement",
                        title=f"Zone-H defacement: {val}",
                        description=f"Zone-H has {len(matches)} defacement record(s) for {val}",
                        entity_type=_entity_type,
                        entity_value=val,
                        confidence=0.82,
                        tags=["zoneh", "defacement", "passive"],
                    )
                )
                evidence.append(
                    dict(
                        source=self.name,
                        description=f"Zone-H defacement records for {val}",
                        raw={
                            "count": len(matches),
                            "samples": [m[0] for m in matches[:5]],
                        },
                        confidence=0.82,
                    )
                )
        return findings
