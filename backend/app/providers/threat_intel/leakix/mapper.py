# backend/app/providers/threat_intel/leakix/mapper.py
"""Normalize LeakIX findings to ProviderFinding."""

from typing import Any, cast

from backend.app.providers.base.models import ProviderFinding
from backend.app.providers.threat_intel.leakix.schemas import LeakIXFinding


def to_provider_finding(finding: LeakIXFinding) -> ProviderFinding:
    """Promote a LeakIX finding dict to a typed ProviderFinding."""
    raw = cast(dict[str, Any], finding.get("raw") or {})
    protocol = str(finding.get("protocol") or "service")
    host = str(finding.get("host") or finding.get("entity_value") or "unknown host")
    port = str(finding.get("port") or "")
    location = f"{host}:{port}" if port else host

    description_parts: list[str] = []
    summary = str(finding.get("summary") or "").strip()
    if summary:
        description_parts.append(summary)

    if finding.get("has_leak"):
        description_parts.append("LeakIX marked this service as a confirmed leak.")

    dataset_rows = int(finding.get("dataset_rows") or 0)
    if dataset_rows:
        description_parts.append(f"Approximate exposed rows: {dataset_rows}.")

    if finding.get("no_auth"):
        description_parts.append("Tagged as unauthenticated.")

    tags = list(
        dict.fromkeys(
            [
                "leakix",
                *list(finding.get("tags") or []),
            ]
        )
    )

    return ProviderFinding(
        title=f"LeakIX exposure: {protocol} on {location}",
        description=" ".join(description_parts) or None,
        tags=tags,
        raw=raw,
    )
