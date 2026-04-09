# backend/app/providers/social/emailformat/mapper.py
"""EmailFormat provider mapper.

EmailFormat is enrichment-only — its output is a list of
``EmailformatEnrichment`` dicts consumed directly by alias_correlation.
It does not produce ``ProviderFinding`` objects and therefore has no
``to_provider_finding()`` function.
"""

from backend.app.providers.social.emailformat.schemas import EmailformatEnrichment

__all__ = ["EmailformatEnrichment"]
