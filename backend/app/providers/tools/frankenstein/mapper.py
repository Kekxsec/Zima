# backend/app/providers/tools/frankenstein/mapper.py
"""Normalize Frankenstein findings to ProviderFinding."""

from typing import Any, cast

from backend.app.providers.base.models import ProviderFinding
from backend.app.providers.tools.frankenstein.schemas import FrankensteinFinding


def to_provider_finding(finding: FrankensteinFinding) -> ProviderFinding:
    """Promote a Frankenstein finding dict to a typed ProviderFinding."""
    raw = cast(dict[str, Any], finding.get("raw") or {})
    domain = str(
        finding.get("domain") or finding.get("entity_value") or "unknown domain"
    )
    status = str(finding.get("status") or "unknown").upper()

    description_parts: list[str] = []

    http_status = finding.get("http_status")
    if http_status is not None:
        description_parts.append(f"HTTP status {http_status}.")

    if finding.get("is_dns_only"):
        description_parts.append(
            "Domain resolves in DNS but did not answer HTTP/S probes."
        )
    elif finding.get("is_dead"):
        description_parts.append("Domain did not resolve or respond to probes.")

    if finding.get("tls_expired"):
        description_parts.append("TLS certificate is expired.")
    elif finding.get("days_until_expiry") is not None:
        description_parts.append(
            f"TLS certificate expires in {finding['days_until_expiry']} days."
        )

    missing_headers = list(finding.get("missing_security_headers") or [])
    if missing_headers:
        description_parts.append(
            f"Missing security headers: {', '.join(missing_headers)}."
        )

    tags: list[str] = ["frankenstein", status.lower()]
    if finding.get("tls_expired"):
        tags.append("tls_expired")
    if finding.get("is_dns_only"):
        tags.append("dns_only")
    if missing_headers:
        tags.append("missing_security_headers")

    return ProviderFinding(
        title=f"Frankenstein posture: {domain} ({status})",
        description=" ".join(description_parts) or None,
        tags=list(dict.fromkeys(tags)),
        raw=raw,
    )
