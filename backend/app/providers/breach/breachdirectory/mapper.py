# backend/app/providers/breach/breachdirectory/mapper.py
"""Normalize BreachDirectory findings to ProviderFinding."""

from typing import Any

from backend.app.providers.base.models import ProviderFinding
from backend.app.providers.breach.breachdirectory.schemas import BreachDirectoryFinding


def to_provider_finding(finding: BreachDirectoryFinding) -> ProviderFinding:
    """Promote a BreachDirectoryFinding dict to a typed ProviderFinding."""
    raw: dict[str, Any] = finding.get("raw", {})  # type: ignore[assignment]
    return ProviderFinding(
        title=finding.get("title", "BreachDirectory hit"),
        description=finding.get("description"),
        tags=list(finding.get("tags") or []),
        raw=raw,
    )
