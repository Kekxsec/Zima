# backend/app/providers/social/skymem/mapper.py
"""Normalize Skymem findings to ProviderFinding."""

from backend.app.providers.base.models import ProviderFinding
from backend.app.providers.social.skymem.schemas import SkymemFinding


def to_provider_finding(finding: SkymemFinding) -> ProviderFinding:
    """Promote a SkymemFinding dict to a typed ProviderFinding.

    Skymem findings carry no ``raw`` dict, so an empty dict is substituted.
    The ``confidence`` field is intentionally dropped — severity/confidence
    is assigned by the consuming module, not the provider layer.
    """
    return ProviderFinding(
        title=finding.get("title", "Skymem finding"),
        description=finding.get("description"),
        tags=list(finding.get("tags") or []),
        raw={},
    )
