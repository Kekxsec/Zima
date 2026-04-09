# backend/app/providers/breach/dehashed/mapper.py
"""Normalize DeHashed findings to ProviderFinding."""

from typing import Any

from backend.app.providers.base.models import ProviderFinding
from backend.app.providers.breach.dehashed.schemas import DehashedFinding


def to_provider_finding(finding: DehashedFinding) -> ProviderFinding:
    """Promote a DehashedFinding dict to a typed ProviderFinding.

    The client already produces the correct shape; this function makes the
    type explicit and strips unknown keys so downstream code is safe.
    """
    raw: dict[str, Any] = finding.get("raw", {})  # type: ignore[assignment]
    return ProviderFinding(
        title=finding.get("title", "DeHashed breach record"),
        description=finding.get("description"),
        tags=list(finding.get("tags") or []),
        raw=raw,
    )
