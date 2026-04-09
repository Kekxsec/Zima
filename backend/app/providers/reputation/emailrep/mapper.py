# backend/app/providers/reputation/emailrep/mapper.py
"""Normalize EmailRep findings to ProviderFinding."""

from typing import Any

from backend.app.providers.base.models import ProviderFinding
from backend.app.providers.reputation.emailrep.schemas import EmailrepFinding


def to_provider_finding(finding: EmailrepFinding) -> ProviderFinding:
    """Promote an EmailrepFinding dict to a typed ProviderFinding."""
    raw: dict[str, Any] = finding.get("raw", {})  # type: ignore[assignment]
    return ProviderFinding(
        title=finding.get("title", "EmailRep finding"),
        description=finding.get("description"),
        tags=list(finding.get("tags") or []),
        raw=raw,
    )
