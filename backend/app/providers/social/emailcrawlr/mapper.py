# backend/app/providers/social/emailcrawlr/mapper.py
"""Normalize EmailCrawlr findings to ProviderFinding."""

from backend.app.providers.base.models import ProviderFinding
from backend.app.providers.social.emailcrawlr.schemas import EmailcrawlrFinding


def to_provider_finding(finding: EmailcrawlrFinding) -> ProviderFinding:
    """Promote an EmailcrawlrFinding dict to a typed ProviderFinding.

    EmailCrawlr findings carry no ``raw`` dict, so an empty dict is substituted.
    The ``confidence`` field is intentionally dropped — severity/confidence
    is assigned by the consuming module, not the provider layer.
    """
    return ProviderFinding(
        title=finding.get("title", "EmailCrawlr finding"),
        description=finding.get("description"),
        tags=list(finding.get("tags") or []),
        raw={},
    )
