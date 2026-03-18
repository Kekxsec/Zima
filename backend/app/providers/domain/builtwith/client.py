# backend/app/providers/domain/builtwith/client.py
from __future__ import annotations

# --- Migration notes (severity/inheritance stripped) ---
# STRIPPED: severity=FindingSeverity.INFO
# --- End migration notes ---
# Extracted/adapted from SpiderFoot module: modules/sfp_builtwith.py (MIT licensed)
# Copyright (c) Steve Micallef.
import ipaddress
import time
import urllib.parse
from typing import Any

from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import (
    ProviderError,
)


class BuiltWithProvider(BaseProviderClient):
    name = "builtwith"
    base_url = "https://api.builtwith.com/rv1/api.json"

    def __init__(
        self, api_key: str = "", timeout_seconds: int = 15, max_age_days: int = 30
    ):
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        self._max_age_days = max_age_days

    async def get_tech_stack(
        self,
        *,
        domain: str | None = None,
        email: str | None = None,
        ip_address: str | None = None,
        phone_number: str | None = None,
    ) -> list[dict[str, Any]]:
        api_key = str(self._api_key).strip()
        if not api_key:
            raise ProviderError(
                message="BuiltWith API key is required",
                retryable=False,
            )
        max_age_days = int(self._max_age_days)
        max_age_days = max(1, min(max_age_days, 3650))
        age_limit_ms = int(time.time() * 1000) - (86400000 * max_age_days)

        findings = []
        evidence = []
        seen = set()
        _inputs: list[tuple[str, str]] = []
        if domain is not None:
            _inputs.append(("domain", domain))
        if email is not None:
            _inputs.append(("email", email))
        if ip_address is not None:
            _inputs.append(("ip_address", ip_address))
        if phone_number is not None:
            _inputs.append(("phone_number", phone_number))
        for _entity_type, _value in _inputs:
            if _entity_type != "domain":
                continue
            domain = _value.strip().lower()
            if not domain:
                continue

            domain_info = await self._query(domain, api_key)
            relationships = await self._query(
                domain, api_key, include_relationships=True
            )

            for email in self._extract_emails(domain_info):
                key = ("email", email)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    dict(
                        provider=self.name,
                        category="identity_exposure",
                        title="BuiltWith discovered contact email",
                        description=f"BuiltWith metadata for {domain} includes contact email {email}",
                        entity_type="email",
                        entity_value=email,
                        confidence=0.7,
                        tags=["builtwith", "contact", "passive"],
                    )
                )

            for phone in self._extract_phones(domain_info):
                key = ("phone", phone)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    dict(
                        provider=self.name,
                        category="identity_exposure",
                        title="BuiltWith discovered phone number",
                        description=f"BuiltWith metadata for {domain} includes phone {phone}",
                        entity_type="phone",
                        entity_value=phone,
                        confidence=0.65,
                        tags=["builtwith", "contact", "passive"],
                    )
                )

            for host in self._extract_subdomains(domain_info, domain):
                key = ("host", host)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    dict(
                        provider=self.name,
                        category="attack_surface",
                        title="BuiltWith discovered subdomain",
                        description=f"BuiltWith metadata for {domain} includes subdomain {host}",
                        entity_type="hostname",
                        entity_value=host,
                        confidence=0.7,
                        tags=["builtwith", "subdomain", "passive"],
                    )
                )

            for ip in self._extract_recent_ips(relationships, domain, age_limit_ms):
                key = ("ip", ip)
                if key in seen:
                    continue
                seen.add(key)
                findings.append(
                    dict(
                        provider=self.name,
                        category="infrastructure_intel",
                        title="BuiltWith related IP address",
                        description=f"BuiltWith relationships for {domain} include IP {ip}",
                        entity_type="ip_address",
                        entity_value=ip,
                        confidence=0.65,
                        tags=["builtwith", "relationship", "passive"],
                    )
                )

            evidence.append(
                dict(
                    source=self.name,
                    description=f"BuiltWith metadata results for {domain}",
                    raw={
                        "domain": domain,
                        "has_domain_info": bool(domain_info),
                        "relationships_count": len(relationships),
                    },
                    confidence=0.7,
                )
            )

        return findings

    async def _query(
        self, domain: str, api_key: str, include_relationships: bool = False
    ) -> dict:
        params = urllib.parse.urlencode({"LOOKUP": domain, "KEY": api_key})
        url = f"{self.base_url}?{params}"
        payload = await self._get_json(url)
        if include_relationships:
            rel = payload.get("Relationships", [])
            if isinstance(rel, list):
                return {"Relationships": rel}
            raise ProviderError(
                message="BuiltWith schema changed: expected Relationships list",
                retryable=False,
            )
        results = payload.get("Results", [])
        if not isinstance(results, list):
            raise ProviderError(
                message="BuiltWith schema changed: expected Results list",
                retryable=False,
            )
        return results[0] if results and isinstance(results[0], dict) else {}

    async def _get_json(self, url: str) -> dict:
        payload = await self._get(url, label="BuiltWith", timeout=self._timeout_seconds)
        if not isinstance(payload, dict):
            raise ProviderError(
                message="BuiltWith schema changed: expected object payload",
                retryable=False,
            )
        return payload

    @staticmethod
    def _extract_emails(domain_info: dict) -> list[str]:
        meta = domain_info.get("Meta", {})
        if not isinstance(meta, dict):
            return []
        emails = meta.get("Emails", [])
        if not isinstance(emails, list):
            return []
        out = []
        for email in emails:
            em = str(email).strip().lower()
            if "@" in em and em not in out:
                out.append(em)
        return out

    @staticmethod
    def _extract_phones(domain_info: dict) -> list[str]:
        meta = domain_info.get("Meta", {})
        if not isinstance(meta, dict):
            return []
        phones = meta.get("Telephones", [])
        if not isinstance(phones, list):
            return []
        out = []
        for phone in phones:
            p = str(phone).strip()
            if p and p not in out:
                out.append(p)
        return out

    @staticmethod
    def _extract_subdomains(domain_info: dict, root_domain: str) -> list[str]:
        result = domain_info.get("Result", {})
        if not isinstance(result, dict):
            return []
        paths = result.get("Paths", [])
        if not isinstance(paths, list):
            return []
        out = []
        for path in paths:
            if not isinstance(path, dict):
                continue
            sub = str(path.get("SubDomain", "")).strip().lower()
            if not sub:
                continue
            host = f"{sub}.{root_domain}"
            if host not in out:
                out.append(host)
        return out

    @staticmethod
    def _extract_recent_ips(
        relationships_payload: dict, domain: str, age_limit_ms: int
    ) -> list[str]:
        rels = relationships_payload.get("Relationships", [])
        if not isinstance(rels, list):
            return []
        out = []
        for rel in rels:
            if not isinstance(rel, dict):
                continue
            if rel.get("Domain") != domain:
                continue
            identifiers = rel.get("Identifiers", [])
            if not isinstance(identifiers, list):
                continue
            for ident in identifiers:
                if not isinstance(ident, dict):
                    continue
                if ident.get("Type") != "ip":
                    continue
                last_seen = ident.get("Last")
                if not isinstance(last_seen, int) or last_seen < age_limit_ms:
                    continue
                value = str(ident.get("Value", "")).strip()
                try:
                    ipaddress.ip_address(value)
                except ValueError:
                    continue
                if value not in out:
                    out.append(value)
        return out
