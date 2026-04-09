# backend/app/providers/social/gravatar/mapper.py
"""Gravatar provider mapper.

Gravatar is enrichment-only — its output is a single ``GravatarEnrichment``
dict (or ``None``) consumed directly by alias_correlation and profile
enrichment modules. It does not produce ``ProviderFinding`` objects and
therefore has no ``to_provider_finding()`` function.
"""

from backend.app.providers.social.gravatar.schemas import GravatarEnrichment

__all__ = ["GravatarEnrichment"]
