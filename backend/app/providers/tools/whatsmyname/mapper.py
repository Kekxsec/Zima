# backend/app/providers/tools/whatsmyname/mapper.py
"""Normalize WhatsmyName (Sherlock) findings to ProviderFinding."""

from typing import Any

from backend.app.providers.base.models import ProviderFinding
from backend.app.providers.tools.whatsmyname.schemas import WhatsmynameFinding


def to_provider_finding(finding: WhatsmynameFinding) -> ProviderFinding:
    """Promote a WhatsmynameFinding dict to a typed ProviderFinding.

    The client already produces the correct shape; this function makes the
    type explicit and strips unknown keys so downstream code is safe.
    """
    raw: dict[str, Any] = finding.get("raw", {})  # type: ignore[assignment]
    return ProviderFinding(
        title=finding.get("title", "WhatsmyName username found"),
        description=finding.get("description"),
        tags=list(finding.get("tags") or []),
        raw=raw,
    )
