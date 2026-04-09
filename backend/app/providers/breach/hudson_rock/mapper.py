# backend/app/providers/breach/hudson_rock/mapper.py
"""Normalize Hudson Rock findings to ProviderFinding."""

from typing import Any

from backend.app.providers.base.models import ProviderFinding
from backend.app.providers.breach.hudson_rock.schemas import HudsonRockFinding


def to_provider_finding(finding: HudsonRockFinding) -> ProviderFinding:
    """Promote a HudsonRockFinding dict to a typed ProviderFinding."""
    raw: dict[str, Any] = finding.get("raw", {})  # type: ignore[assignment]
    return ProviderFinding(
        title=finding.get("title", "Hudson Rock stealer log hit"),
        description=finding.get("description"),
        tags=list(finding.get("tags") or []),
        raw=raw,
    )
