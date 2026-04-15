# backend/app/providers/threat_intel/intelx/mapper.py
"""Normalize IntelX findings to ProviderFinding."""

from typing import Any

from backend.app.providers.base.models import ProviderFinding
from backend.app.providers.threat_intel.intelx.schemas import IntelXFinding


def to_provider_finding(finding: IntelXFinding) -> ProviderFinding:
    """Promote an IntelXFinding dict to a typed ProviderFinding.

    The client already produces the correct shape; this function makes the
    type explicit and strips unknown keys so downstream code is safe.
    """
    raw: dict[str, Any] = finding.get("raw", {})  # type: ignore[assignment]
    return ProviderFinding(
        title=finding.get("title", "IntelX dark web record"),
        description=finding.get("description"),
        tags=list(finding.get("tags") or []),
        raw=raw,
    )
