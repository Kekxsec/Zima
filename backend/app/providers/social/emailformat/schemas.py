# backend/app/providers/social/emailformat/schemas.py
"""Typed schemas for EmailFormat provider enrichment dicts."""

from typing import TypedDict


class EmailformatEnrichment(TypedDict):
    """Enrichment dict returned by EmailformatProvider.get_formats().

    EmailFormat is enrichment-only — it does not emit ProviderFindings.
    Consumers use these dicts directly for alias correlation.
    """

    email: str
    domain: str
