# backend/app/providers/threat_intel/circllu/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Adapted from SpiderFoot module: modules/sfp_circllu.py (MIT licensed)
import base64
from typing import Any

from backend.app.providers.base.client import BaseProviderClient


class CirclluProvider(BaseProviderClient):
    name = "circllu"
    base_url = "https://www.circl.lu"

    def __init__(
        self, api_user: str = "", api_password: str = "", timeout_seconds: int = 30
    ):
        self._api_user = api_user
        self._api_password = api_password
        self._timeout_seconds = timeout_seconds

    async def check_reputation(
        self, *, domain: str | None = None, ip_address: str | None = None
    ) -> list[dict[str, Any]]:
        api_user = str(self._api_user).strip()
        api_pass = str(self._api_password).strip()
        headers: dict = {"Accept": "application/json"}
        if api_user and api_pass:
            creds = base64.b64encode(f"{api_user}:{api_pass}".encode()).decode()
            headers["Authorization"] = f"Basic {creds}"
        findings, evidence = [], []
        seen: set[str] = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        for _entity_type, _value in _inputs:
            val = _value.strip()
            if _entity_type == "domain":
                url = f"{self.base_url}/pdns/query/{val}"
                data = self._fetch(url, headers)
                records = data if isinstance(data, list) else []
                for rec in records[:20]:
                    if not isinstance(rec, dict):
                        continue
                    rdata = str(rec.get("rdata", "")).strip()
                    rtype = str(rec.get("rrtype", "")).strip()
                    if not rdata or rdata in seen:
                        continue
                    seen.add(rdata)
                    findings.append(
                        dict(
                            provider=self.name,
                            category="passive_dns",
                            title=f"CIRCL passive DNS: {rdata}",
                            description=f"Passive DNS record ({rtype}) for {val}: {rdata}",
                            entity_type="ip_address",
                            entity_value=rdata,
                            confidence=0.75,
                            tags=["circllu", "passive_dns", "passive"],
                        )
                    )
                if records:
                    evidence.append(
                        dict(
                            source=self.name,
                            description=f"CIRCL passive DNS for {val}",
                            raw={"count": len(records)},
                            confidence=0.75,
                        )
                    )
            elif _entity_type == "ip_address":
                url = f"{self.base_url}/v2pssl/query/{val}"
                data = self._fetch(url, headers)
                certs = data.get("certificates", []) if isinstance(data, dict) else []
                if isinstance(certs, list):
                    for cert in certs[:10]:
                        subject = str(
                            cert.get("subject", "") if isinstance(cert, dict) else ""
                        ).strip()
                        if subject and subject not in seen:
                            seen.add(subject)
                            findings.append(
                                dict(
                                    provider=self.name,
                                    category="ssl_certificate",
                                    title=f"CIRCL SSL cert: {subject}",
                                    description=f"SSL certificate for IP {val}: {subject}",
                                    entity_type="hostname",
                                    entity_value=subject,
                                    confidence=0.75,
                                    tags=["circllu", "ssl", "passive"],
                                )
                            )
                    if certs:
                        evidence.append(
                            dict(
                                source=self.name,
                                description=f"CIRCL SSL certs for {val}",
                                raw={"count": len(certs)},
                                confidence=0.75,
                            )
                        )
        return findings

    async def _fetch(self, url: str, headers: dict) -> dict:
        return await self._get(
            url, label="Circllu", headers=headers, timeout=self._timeout_seconds
        )
