# backend/app/providers/breach/leakcheck/mapper.py
"""Normalize LeakCheck findings to ProviderFinding."""

from typing import Any

from backend.app.providers.base.models import ProviderFinding
from backend.app.providers.breach.leakcheck.schemas import LeakCheckFinding


def to_provider_finding(finding: LeakCheckFinding) -> ProviderFinding:
    """Promote a LeakCheckFinding dict to a typed ProviderFinding."""
    raw: dict[str, Any] = finding.get("raw", {})  # type: ignore[assignment]
    return ProviderFinding(
        title=finding.get("title", "LeakCheck breach record"),
        description=finding.get("description"),
        tags=list(finding.get("tags") or []),
        raw=raw,
    )
